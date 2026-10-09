"""Native Anthropic contracts with synthetic keys and offline HTTP transports."""
import asyncio
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch
import httpx
from ai4dos.anthropic_provider import AnthropicProvider, anthropic_options, MANUAL, ADAPTIVE, DISABLE
from ai4dos.config import Settings, build_provider
from ai4dos.provider import ProviderError, DOS_CAPABILITIES, provider_instructions
from ai4dos.server import Gateway
from ai4dos.session import Message, Role, Session

KEY = 'synthetic-anthropic-contract-key'
DETAIL = 'synthetic-private-http-detail'
MESSAGES = [Message(Role.ROLE_SYSTEM, 'first system note'), Message(Role.ROLE_USER, 'one'),
            Message(Role.ROLE_AI, 'two'), Message(Role.ROLE_SYSTEM, 'later system note'),
            Message(Role.ROLE_USER, 'three')]


def start():
    return {'type': 'message_start', 'message': {'role': 'assistant', 'content': [], 'stop_reason': None}}


def block_start(index=0, kind='text', text=''):
    return {'type': 'content_block_start', 'index': index, 'content_block': {'type': kind, 'text': text}}


def delta(text, index=0):
    return {'type': 'content_block_delta', 'index': index, 'delta': {'type': 'text_delta', 'text': text}}


def block_stop(index=0):
    return {'type': 'content_block_stop', 'index': index}


def terminal(reason='end_turn'):
    return [{'type': 'message_delta', 'delta': {'stop_reason': reason}}, {'type': 'message_stop'}]


def events(text='hello'):
    return [start(), block_start(), delta(text), block_stop(), *terminal()]


def sse(items):
    return ''.join('event: '+item['type']+'\ndata: '+json.dumps(item)+'\n\n' for item in items).encode()


class TrackingStream(httpx.AsyncByteStream):
    def __init__(self, parts):
        self.parts, self.closed, self.sent = parts, False, 0
    async def __aiter__(self):
        for part in self.parts:
            self.sent += 1
            await asyncio.sleep(0)
            yield part
    async def aclose(self):
        self.closed = True


class AnthropicContracts(unittest.IsolatedAsyncioTestCase):
    def settings(self, **values):
        return Settings(devices={'d': 'd'*32}, provider='anthropic',
                        model=values.pop('model', 'claude-sonnet-5-5'), api_key=KEY, **values)

    def provider(self, items=None, status=200, body=None, **settings):
        requests = []
        data = sse(events() if items is None else items) if body is None else body
        stream = TrackingStream([data[i:i+19] for i in range(0,len(data),19)])
        response = httpx.Response(status, headers={'content-type':'text/event-stream'}, stream=stream)
        def handle(req):requests.append(req);return response
        client = httpx.AsyncClient(transport=httpx.MockTransport(handle), trust_env=False)
        with patch('ai4dos.anthropic_provider.make_http_client',return_value=client):
            provider = build_provider(self.settings(**settings))
        return provider, requests, response, stream

    async def test_native_request_roles_system_capabilities_limits_and_text_filter(self):
        provider, requests, response, stream = self.provider(
            [start(), block_start(text='h'), delta('ello<|fim_'), {'type':'ping'},
             delta('suffix|> ä world'), block_stop(), *terminal()],
            instructions='neutral technical instructions', max_output_tokens=333)
        try:
            self.assertEqual(''.join([x async for x in provider.stream(MESSAGES)]),'hello ä world')
            req = requests[0]; body = json.loads(req.content)
            self.assertIsInstance(provider,AnthropicProvider);self.assertEqual(provider.label,'Claude')
            self.assertEqual(str(req.url),'https://api.anthropic.com/v1/messages')
            self.assertEqual(req.headers['x-api-key'],KEY)
            self.assertEqual(req.headers['anthropic-version'],'2023-06-01')
            self.assertNotIn('authorization',req.headers);self.assertNotIn('anthropic-beta',req.headers)
            self.assertEqual(body['system'],provider_instructions('neutral technical instructions')+'\n\nfirst system note\n\nlater system note')
            self.assertIn(DOS_CAPABILITIES,body['system'])
            self.assertEqual(body['messages'],[{'role':'user','content':'one'}, {'role':'assistant','content':'two'}, {'role':'user','content':'three'}])
            self.assertEqual(body['max_tokens'],333);self.assertTrue(body['stream'])
            self.assertEqual(body['thinking'],{'type':'between_tools'})
            self.assertEqual(set(body),{'model','messages','system','stream','max_tokens','thinking'})
            self.assertEqual(len(requests),1);self.assertTrue(response.is_closed);self.assertTrue(stream.closed)
            self.assertEqual(MESSAGES[0].role,Role.ROLE_SYSTEM)
        finally:await provider.close()
        self.assertTrue(provider.client.is_closed)

    async def test_none_model_mappings_do_not_activate_optional_thinking_or_substitute_effort(self):
        cases=[(m,{'type':'disabled'}) for m in DISABLE]+[
            ('claude-sonnet-5-5',{'type':'between_tools'}),('claude-opus-5-5',None),
            ('claude-fable-5-1',None),('claude-mythos-preview',None),('unknown-model',None)]
        for model,thinking in cases:
            with self.subTest(model=model):
                provider,requests,_,_=self.provider(model=model)
                try:
                    self.assertEqual(''.join([x async for x in provider.stream(MESSAGES)]),'hello')
                    body=json.loads(requests[0].content)
                    self.assertEqual(body.get('thinking'),thinking)
                    self.assertNotIn('output_config',body);self.assertNotIn('temperature',body)
                    self.assertEqual(body['max_tokens'],1024)
                    self.assertNotIn('reasoning',body);self.assertNotIn('reasoning_effort',body)
                finally:await provider.close()

    async def test_explicit_thinking_and_temperature_options(self):
        for values,expected in [
            ({'reasoning':'high'}, {'thinking':{'type':'adaptive'},'output_config':{'effort':'high'}}),
            ({'reasoning':'xhigh'}, {'thinking':{'type':'adaptive'},'output_config':{'effort':'xhigh'}}),
            ({'model':'claude-sonnet-4-6','reasoning':'max'}, {'thinking':{'type':'adaptive'},'output_config':{'effort':'max'}}),
            ({'reasoning':'high','reasoning_effort':'low'}, {'thinking':{'type':'adaptive'},'output_config':{'effort':'low'}}),
            ({'reasoning':'high','reasoning_effort':'none'}, {'thinking':{'type':'between_tools'}}),
            ({'model':'claude-haiku-4-5-20251001','thinking_budget':1024,'max_output_tokens':2048}, {'thinking':{'type':'enabled','budget_tokens':1024}}),
            ({'model':'claude-sonnet-4-6','temperature':0.2}, {'thinking':{'type':'disabled'},'temperature':0.2}),
            ({'model':'claude-opus-4-5','thinking_budget':2048,'max_output_tokens':4096,'reasoning_effort':'medium'},
             {'thinking':{'type':'enabled','budget_tokens':2048},'output_config':{'effort':'medium'}})]:
            provider,requests,_,_=self.provider(**values)
            try:
                self.assertEqual(''.join([x async for x in provider.stream(MESSAGES)]),'hello')
                body=json.loads(requests[0].content)
                for key,value in expected.items():self.assertEqual(body[key],value)
                self.assertEqual(body['max_tokens'],values.get('max_output_tokens',1024))
            finally:await provider.close()

    async def test_unknown_model_explicit_options_reach_native_request(self):
        for values,expected in [
            ({'reasoning':'high'}, {'thinking':{'type':'adaptive'},'output_config':{'effort':'high'}}),
            ({'reasoning_effort':'xhigh'}, {'thinking':{'type':'adaptive'},'output_config':{'effort':'xhigh'}}),
            ({'reasoning_effort':'max'}, {'thinking':{'type':'adaptive'},'output_config':{'effort':'max'}}),
            ({'thinking_budget':1024,'max_output_tokens':4096}, {'thinking':{'type':'enabled','budget_tokens':1024}}),
            ({'thinking_budget':1024,'max_output_tokens':4096,'reasoning':'max'},
             {'thinking':{'type':'enabled','budget_tokens':1024},'output_config':{'effort':'max'}}),
            ({'temperature':0.5}, {'temperature':0.5}),
            ({'reasoning':'high','temperature':1}, {'thinking':{'type':'adaptive'},'output_config':{'effort':'high'},'temperature':1}),
            ({'reasoning':'high','reasoning_effort':'none'}, {})]:
            with self.subTest(values=values):
                provider,requests,_,_=self.provider(model='claude-future-model',**values)
                try:
                    self.assertEqual(''.join([x async for x in provider.stream(MESSAGES)]),'hello')
                    body=json.loads(requests[0].content)
                    self.assertEqual(body['model'],'claude-future-model')
                    self.assertEqual({k:v for k,v in body.items() if k in {'thinking','output_config','temperature'}},expected)
                finally:await provider.close()

    async def test_known_native_compatible_combinations(self):
        for values,expected in [
            ({'model':'claude-opus-5-5','temperature':1}, {'temperature':1}),
            ({'model':'claude-sonnet-4-6','thinking_budget':1024,'max_output_tokens':4096,'reasoning':'high'},
             {'thinking':{'type':'enabled','budget_tokens':1024},'output_config':{'effort':'high'}}),
            ({'model':'claude-mythos-preview','thinking_budget':1024,'max_output_tokens':4096,'reasoning':'max'},
             {'thinking':{'type':'enabled','budget_tokens':1024},'output_config':{'effort':'max'}})]:
            provider,requests,_,_=self.provider(**values)
            try:
                self.assertEqual(''.join([x async for x in provider.stream(MESSAGES)]),'hello')
                body=json.loads(requests[0].content)
                self.assertEqual({k:v for k,v in body.items() if k in {'thinking','output_config','temperature'}},expected)
            finally:await provider.close()

    async def test_only_visible_text_is_returned_and_multiple_blocks_work(self):
        items=[start(),block_start(kind='thinking'),
               {'type':'content_block_delta','index':0,'delta':{'type':'thinking_delta','thinking':DETAIL}},
               {'type':'content_block_delta','index':0,'delta':{'type':'signature_delta','signature':KEY}},
               block_stop(),block_start(1,'redacted_thinking'),block_stop(1),
               block_start(2),delta('visible<|fim_',2),block_stop(2),
               block_start(3),delta('suffix|> text',3),block_stop(3),*terminal()]
        provider,_,_,_=self.provider(items,model='claude-opus-5-5')
        try:self.assertEqual(''.join([x async for x in provider.stream(MESSAGES)]),'visible text')
        finally:await provider.close()

    async def test_incomplete_bad_terminal_tools_and_invalid_block_order_fail_and_close(self):
        good=events()
        cases=[good[:-1], good[:-2], [start(),*terminal()],
               good+ [{'type':'message_stop'}],good+ [delta('late')],
               [start(),block_start(kind='tool_use')], [start(),block_start(kind='image')],
               [start(),block_start(),delta('wrong',1)], [start(),delta('orphan')],
               [start(),block_start(),*terminal()], [start(),block_start(),block_start()],
               [start(),block_start(),block_stop(1)], [start(),start()],
               [{'type':'ping'}], [block_start()],
               [start(),block_start(),delta(42)],
               [start(),block_start(),{'type':'content_block_delta','index':0,'delta':{'type':'input_json_delta','partial_json':'{}'}}]]
        cases += [[start(),block_start(),delta('partial'),block_stop(),*terminal(reason)]
                  for reason in ['max_tokens','tool_use','stop_sequence','refusal','pause_turn','unknown']]
        for items in cases:
            with self.subTest(items=items):
                provider,requests,response,stream=self.provider(items)
                try:
                    with self.assertRaises(ProviderError):[x async for x in provider.stream(MESSAGES)]
                    self.assertTrue(response.is_closed);self.assertTrue(stream.closed);self.assertEqual(len(requests),1)
                finally:await provider.close()

    async def test_http_and_sse_errors_are_normalized_without_private_details_or_retry(self):
        cases=[(401,'authentication_error','UPSTREAM_AUTH'),(403,'permission_error','UPSTREAM_AUTH'),
               (404,'not_found_error','UPSTREAM_MODEL'),(429,'rate_limit_error','UPSTREAM_RATE_LIMIT'),
               (529,'overloaded_error','UPSTREAM_UNAVAILABLE'),(503,'overloaded_error','UPSTREAM_UNAVAILABLE'),
               (500,'api_error','UPSTREAM'),(400,'invalid_request_error','UPSTREAM')]
        for status,error,code in cases:
            for mode in ['http','sse']:
                with self.subTest(status=status,mode=mode):
                    body={'type':'error','error':{'type':error,'message':DETAIL+KEY}}
                    provider,requests,response,stream=self.provider(
                        [body] if mode=='sse' else None,status=status if mode=='http' else 200,
                        body=json.dumps(body).encode() if mode=='http' else None)
                    try:
                        with self.assertRaises(ProviderError) as cm:[x async for x in provider.stream(MESSAGES)]
                        self.assertEqual(cm.exception.code,code)
                        self.assertNotIn(KEY,str(cm.exception));self.assertNotIn(DETAIL,str(cm.exception))
                        self.assertTrue(response.is_closed);self.assertTrue(stream.closed);self.assertEqual(len(requests),1)
                    finally:await provider.close()

    async def test_transport_error_malformed_json_and_early_cleanup(self):
        for error in [httpx.ConnectError,httpx.ReadTimeout]:
            def handle(req):raise error(DETAIL+KEY,request=req)
            client=httpx.AsyncClient(transport=httpx.MockTransport(handle))
            provider=AnthropicProvider(api_key=KEY,model='test',instructions='',client=client)
            try:
                with self.assertRaises(ProviderError) as cm:[x async for x in provider.stream(MESSAGES)]
                self.assertEqual(cm.exception.code,'UPSTREAM_UNAVAILABLE');self.assertNotIn(KEY,str(cm.exception))
            finally:await provider.close()
        provider,_,response,stream=self.provider(body=b'data: {broken\n\n')
        try:
            with self.assertRaises(ProviderError):[x async for x in provider.stream(MESSAGES)]
            self.assertTrue(response.is_closed);self.assertTrue(stream.closed)
        finally:await provider.close()
        provider,_,response,stream=self.provider()
        generator=provider.stream(MESSAGES)
        try:
            self.assertEqual(await generator.__anext__(),'hello')
            self.assertFalse(response.is_closed)
            self.assertLess(stream.sent,len(stream.parts))  # Still streaming, not prebuffered EOF.
            await generator.aclose()
            self.assertTrue(response.is_closed);self.assertTrue(stream.closed)
        finally:await provider.close()

    async def test_cancel_during_stream_closes_response(self):
        entered=asyncio.Event();closed=asyncio.Event()
        class WaitingStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield sse([start(),block_start()])
                entered.set()
                await asyncio.Future()
            async def aclose(self):closed.set()
        response=httpx.Response(200,stream=WaitingStream())
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda req:response))
        provider=AnthropicProvider(api_key=KEY,model='test',instructions='',client=client)
        async def consume():return [x async for x in provider.stream(MESSAGES)]
        task=asyncio.create_task(consume())
        try:
            await asyncio.wait_for(entered.wait(),1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
            self.assertTrue(response.is_closed);self.assertTrue(closed.is_set())
        finally:
            task.cancel()
            await asyncio.gather(task,return_exceptions=True)
            await provider.close()

    async def test_shared_gateway_limits_and_no_history_on_incomplete_reply(self):
        class Writer:
            def __init__(self):self.data=b''
            def write(self,data):self.data+=data
            async def drain(self):pass
        for items,limit,success in [(events('**hello**'),65536,True), (events('too many bytes'),3,False), (events('partial')[:-1],65536,False)]:
            provider,_,response,stream=self.provider(items)
            gateway=Gateway(self.settings(max_reply_bytes=limit),provider)
            session=Session();writer=Writer()
            try:
                if success:
                    await gateway.respond(writer,session,'one')
                    self.assertEqual(writer.data,b'BEGIN Claude\r\nDATA hello\r\nEND\r\n')
                    self.assertEqual([m.role for m in session.history],[Role.ROLE_USER,Role.ROLE_AI])
                else:
                    with self.assertRaises((ProviderError,ValueError)):await gateway.respond(writer,session,'one')
                    self.assertEqual(writer.data,b'BEGIN Claude\r\n');self.assertEqual(session.history,[])
                self.assertTrue(response.is_closed);self.assertTrue(stream.closed)
            finally:await gateway.close()

    async def test_real_gateway_hmac_resume_and_native_history_offline(self):
        requests=[]
        def handle(req):
            requests.append(json.loads(req.content))
            return httpx.Response(200,content=sse(events('first' if len(requests)==1 else 'resumed')))
        client=httpx.AsyncClient(transport=httpx.MockTransport(handle),trust_env=False)
        with patch('ai4dos.anthropic_provider.make_http_client',return_value=client):provider=build_provider(self.settings())
        secret=secrets.token_hex(32);gateway=Gateway(Settings(port=0,devices={'d':secret}),provider)
        server=await gateway.start();writers=[]
        async def connect():
            reader,writer=await asyncio.open_connection('127.0.0.1',server.sockets[0].getsockname()[1]);writers.append(writer)
            async def read():return (await asyncio.wait_for(reader.readline(),3)).decode().strip()
            async def send(text):writer.write((text+'\r\n').encode());await writer.drain()
            self.assertEqual(await read(),'OK AI4DOS/0.3 UTF-8');await send('HELLO d')
            nonce=(await read()).split()[1]
            await send('AUTH '+hmac.new(secret.encode(),nonce.encode(),hashlib.sha256).hexdigest())
            self.assertEqual(await read(),'OK AUTH');return read,send
        try:
            read,send=await connect();await send('NEW');sid=(await read()).split()[1]
            await send('MSG one');self.assertEqual([await read(),await read(),await read()],['BEGIN Claude','DATA first','END'])
            writers[-1].close();await writers[-1].wait_closed()
            for _ in range(100):
                if not gateway.active:break
                await asyncio.sleep(.01)
            read,send=await connect();await send('RESUME '+sid);self.assertEqual(await read(),'OK RESUME')
            await send('MSG two');self.assertEqual([await read(),await read(),await read()],['BEGIN Claude','DATA resumed','END'])
            self.assertEqual(requests[-1]['messages'],[{'role':'user','content':'one'},{'role':'assistant','content':'first'},{'role':'user','content':'two'}])
            await send('QUIT');self.assertEqual(await read(),'OK BYE')
        finally:
            for w in writers:w.close();await w.wait_closed()
            server.close();await server.wait_closed();await gateway.close()


class AnthropicConfig(unittest.TestCase):
    def settings(self, **values):
        return Settings(devices={'d':'d'*32},provider='anthropic',model=values.pop('model','claude-sonnet-5-5'),**values)

    def test_factory_env_and_provider_file_output_override(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            (p/'provider.cfg').write_text('PROVIDER=anthropic\nMODEL=claude-sonnet-5-5\nAPI_KEY=\nREASONING=none\nMAX_OUTPUT_TOKENS=333\n')
            (p/'gateway.json').write_text(json.dumps({'devices':{'d':'d'*32},'provider_config':'provider.cfg','max_output_tokens':1024}))
            settings=Settings.load(p/'gateway.json');self.assertEqual(settings.api_mode,'native');self.assertEqual(settings.max_output_tokens,333)
            with patch.dict(os.environ,{'ANTHROPIC_API_KEY':KEY},clear=True),patch('ai4dos.anthropic_provider.make_http_client') as client:
                provider=build_provider(settings)
                self.assertEqual(provider.api_key,KEY);self.assertEqual(provider.label,'Claude');client.assert_called_once()
            self.assertNotIn(KEY,repr(settings))
        with patch.dict(os.environ,{},clear=True),self.assertRaises(ValueError):build_provider(self.settings())

    def test_incompatible_options_rejected_without_fallback(self):
        for values in [{'reasoning':'minimal'}, {'reasoning_effort':'minimal'}, {'reasoning':'xhigh','model':'claude-sonnet-4-6'},
                       {'thinking_budget':0}, {'thinking_budget':1024},
                       {'thinking_budget':1024,'max_output_tokens':4096},
                       {'model':'claude-haiku-4-5','reasoning':'high'},
                       {'model':'claude-haiku-4-5','thinking_budget':1023,'max_output_tokens':4096},
                       {'model':'claude-haiku-4-5','thinking_budget':4096,'max_output_tokens':4096},
                       {'model':'claude-haiku-4-5','thinking_budget':1024,'max_output_tokens':4096,'reasoning':'low'},
                       {'model':'claude-opus-4-5','thinking_budget':1024,'max_output_tokens':4096,'reasoning':'max'},
                       {'model':'claude-future-model','thinking_budget':1023,'max_output_tokens':4096},
                       {'model':'claude-future-model','thinking_budget':4096,'max_output_tokens':4096},
                       {'model':'claude-future-model','temperature':1.5},
                       {'model':'claude-future-model','reasoning':'high','temperature':0.5},
                       {'temperature':0.5}, {'model':'claude-sonnet-4-6','temperature':1.5},
                       {'model':'claude-sonnet-4-6','reasoning':'high','temperature':0.5},
                       {'thinking_level':'high'},{'enable_thinking':True},{'clear_thinking':True},
                       {'api_mode':'chat'},{'base_url':'https://test.invalid'}]:
            with self.subTest(values=values),self.assertRaises(ValueError):self.settings(**values)
