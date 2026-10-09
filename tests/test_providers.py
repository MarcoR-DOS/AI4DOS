"""Real SDK + local MockTransport contracts; no external keys or requests."""
import asyncio
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch
import httpx
from openai import AsyncOpenAI
from ai4dos.config import Settings, PRESETS, build_provider
from ai4dos.compatible_provider import CompatibleProvider
from ai4dos.openai_provider import OpenAIProvider
from ai4dos.provider import ProviderError, provider_instructions
from ai4dos.server import Gateway
from ai4dos.session import Message, Role

KEY = 'synthetic-private-key-never-forward'
DETAIL = 'synthetic-private-upstream-detail'
MESSAGES = [Message(Role.ROLE_USER,'one'),Message(Role.ROLE_AI,'two'),Message(Role.ROLE_SYSTEM,'note')]


def chunk(content=None, finish=None, **extras):
    return {'id':'test','created':0,'object':'chat.completion.chunk','model':'returned-model',
            'choices':[{'index':0,'delta':{'content':content},'finish_reason':finish}],**extras}


def sse(events, done=True):
    return ''.join('data: '+json.dumps(event)+'\n\n' for event in events)+('data: [DONE]\n\n' if done else '')


class ProviderContracts(unittest.IsolatedAsyncioTestCase):
    def sdk(self, handler, base='https://test.invalid/v1'):
        return AsyncOpenAI(api_key=KEY,base_url=base,max_retries=0,
                           http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler),trust_env=False))

    async def test_all_chat_presets_factory_request_and_finish(self):
        for name in ('openrouter','mistral','nvidia','openai-compatible'):
            with self.subTest(provider=name):
                responses=[];requests=[]
                base=PRESETS[name][0] or 'http://localhost:9000/v1'
                def handle(request):
                    requests.append(request)
                    body=json.loads(request.content)
                    self.assertEqual(str(request.url),base.rstrip('/')+'/chat/completions')
                    self.assertEqual(request.headers['authorization'],'Bearer '+KEY)
                    self.assertEqual(body['messages'],[{'role':'system','content':provider_instructions('neutral')},
                        {'role':'user','content':'one'},{'role':'assistant','content':'two'},{'role':'system','content':'note'}])
                    self.assertEqual(body['model'],'openrouter/free' if name=='openrouter' else 'contract-model')
                    self.assertEqual(set(body),{'model','messages','stream','max_tokens'} | ({'temperature'} if name == 'nvidia' else {'reasoning'} if name == 'openrouter' else set()))
                    if name == 'nvidia':
                        self.assertNotIn('chat_template_kwargs',body)
                        self.assertNotIn('reasoning_effort',body)
                        self.assertEqual(body['temperature'],0.5)
                    self.assertTrue(body['stream']);self.assertEqual(body['max_tokens'],1024)
                    response=httpx.Response(200,headers={'content-type':'text/event-stream'},
                        content=sse([chunk('hello<|fim_'),chunk('suffix|> world'),chunk(finish='stop'),
                         {'id':'test','created':0,'object':'chat.completion.chunk','model':'returned-model','choices':[],'usage':{'completion_tokens':2,'prompt_tokens':2,'total_tokens':4}}]))
                    responses.append(response);return response
                sdk=self.sdk(handle,base)
                settings=Settings(devices={'d':'d'*32},provider=name,model='' if name=='openrouter' else 'contract-model',
                                  api_key=KEY,instructions='neutral',base_url=base if name=='openai-compatible' else '')
                with patch('ai4dos.compatible_provider.make_client',return_value=sdk) as factory:
                    provider=build_provider(settings)
                    factory.assert_called_once_with(KEY,base)
                try:
                    self.assertEqual(''.join([part async for part in provider.stream(MESSAGES)]),'hello world')
                    self.assertEqual(len(requests),1);self.assertTrue(responses[0].is_closed)
                    self.assertEqual(provider.model,settings.model)
                    self.assertEqual(provider.label,PRESETS[name][2])
                    self.assertEqual(MESSAGES[0].role,Role.ROLE_USER)
                finally:await provider.close()
                self.assertTrue(sdk.is_closed)

    async def test_openrouter_final_usage_repeats_stop(self):
        # OpenRouter's documented final usage chunk has one content-free choice.
        usage = {'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}
        for delta in ({}, {'content':''}, {'content':None}):
            with self.subTest(delta=delta):
                final = chunk(finish='stop', usage=usage)
                final['choices'][0]['delta'] = delta
                response = httpx.Response(200, headers={'content-type':'text/event-stream'},
                                         content=sse([chunk('OK'), chunk(finish='stop'), final]))
                requests = []
                def handle(req):
                    requests.append(req)
                    return response
                sdk = self.sdk(handle, PRESETS['openrouter'][0])
                with patch('ai4dos.compatible_provider.make_client', return_value=sdk):
                    provider = build_provider(Settings(devices={'d':'d'*32},
                                                       provider='openrouter', api_key=KEY))
                try:
                    self.assertEqual(''.join([x async for x in provider.stream(MESSAGES)]), 'OK')
                    self.assertEqual(len(requests), 1)
                    self.assertTrue(response.is_closed)
                finally:
                    await provider.close()

    async def test_openrouter_usage_exception_keeps_invalid_streams_rejected(self):
        usage = {'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}
        final = chunk(finish='stop', usage=usage)
        cases = [
            [chunk(finish='stop')],  # Duplicate terminal without usage.
            [chunk('after', finish='stop', usage=usage)],
            [chunk(finish='length', usage=usage)],
            [chunk(finish='error', usage=usage)],
            [chunk(finish='stop', usage=usage, error={'code':500,'message':DETAIL+KEY})],
            [final, final],  # Only one final usage choice is permitted.
            [final, chunk('after')],
        ]
        tool = chunk(finish='stop', usage=usage)
        tool['choices'][0]['delta'] = {'tool_calls':[{'index':0,'id':'x','type':'function',
                                                   'function':{'name':'x','arguments':'{}'}}]}
        cases.append([tool])
        for tail in cases:
            response = httpx.Response(200, headers={'content-type':'text/event-stream'},
                                     content=sse([chunk('partial', finish='stop'), *tail]))
            sdk = self.sdk(lambda req:response)
            provider = CompatibleProvider(client=sdk, base_url='https://test.invalid',
                                          model='openrouter/free', instructions='', label='OpenRouter')
            try:
                with self.assertRaises(ProviderError) as cm:
                    [x async for x in provider.stream(MESSAGES)]
                self.assertEqual(cm.exception.code, 'UPSTREAM')
                self.assertNotIn(KEY, str(cm.exception))
                self.assertNotIn(DETAIL, str(cm.exception))
                self.assertTrue(response.is_closed)
            finally:
                await provider.close()
        # The exception is scoped to the OpenRouter preset.
        response = httpx.Response(200, headers={'content-type':'text/event-stream'},
                                 content=sse([chunk('partial', finish='stop'), final]))
        sdk = self.sdk(lambda req:response)
        provider = CompatibleProvider(client=sdk, base_url='https://test.invalid',
                                      model='test', instructions='', label='Mistral')
        try:
            with self.assertRaises(ProviderError):
                [x async for x in provider.stream(MESSAGES)]
        finally:
            await provider.close()

    async def test_generic_responses_and_openai_preserve_contract(self):
        for name in ('openai','openai-compatible'):
            base=PRESETS[name][0] or 'http://localhost:9000/v1'
            def handle(request):
                body=json.loads(request.content)
                self.assertEqual(str(request.url),base+'/responses')
                self.assertEqual(body['input'],[{'role':'user','content':'one'},{'role':'assistant','content':'two'},{'role':'system','content':'note'}])
                self.assertFalse(body['store']);self.assertEqual(body['instructions'],provider_instructions('neutral'))
                self.assertEqual(body['reasoning'],{'effort':'none'})
                return httpx.Response(200,headers={'content-type':'text/event-stream'},content=sse([
                    {'type':'response.output_text.delta','delta':'okay'},
                    {'type':'response.completed','response':{'status':'completed'}}]))
            sdk=self.sdk(handle,base)
            with patch('ai4dos.openai_provider.make_client',return_value=sdk):
                provider=build_provider(Settings(devices={'d':'d'*32},provider=name,model='test',api_key=KEY,
                    api_mode='responses',base_url=base if name=='openai-compatible' else '',instructions='neutral',reasoning_effort='none'))
            try:self.assertEqual(''.join([x async for x in provider.stream(MESSAGES)]),'okay')
            finally:await provider.close()

    async def test_http_errors_sanitized_no_retry_both_apis(self):
        cases=[(401,'invalid_api_key','UPSTREAM_AUTH'),(403,None,'UPSTREAM_AUTH'),
               (404,'model_not_found','UPSTREAM_MODEL'),(400,'invalid_model','UPSTREAM_MODEL'),
               (429,None,'UPSTREAM_RATE_LIMIT'),(503,None,'UPSTREAM_UNAVAILABLE'),(402,None,'UPSTREAM'),(500,None,'UPSTREAM')]
        for mode in ('chat','responses'):
            for status,code,expected in cases:
                with self.subTest(mode=mode,status=status):
                    requests=[];responses=[]
                    def handle(request):
                        requests.append(request)
                        response=httpx.Response(status,json={'error':{'message':DETAIL+KEY,'code':code}})
                        responses.append(response);return response
                    sdk=self.sdk(handle)
                    provider=(CompatibleProvider(client=sdk,base_url='https://test.invalid/v1',model='test',instructions='neutral') if mode=='chat'
                              else OpenAIProvider(client=sdk,model='test',instructions='neutral'))
                    try:
                        with self.assertRaises(ProviderError) as cm:[x async for x in provider.stream(MESSAGES)]
                        self.assertEqual(cm.exception.code,expected)
                        self.assertNotIn(KEY,str(cm.exception));self.assertNotIn(DETAIL,str(cm.exception))
                        self.assertEqual(len(requests),1);self.assertTrue(responses[0].is_closed)
                    finally:await provider.close()

    async def test_network_error_and_timeout(self):
        for error in (httpx.ConnectError,httpx.ReadTimeout):
            def handle(request):raise error(DETAIL+KEY,request=request)
            sdk=self.sdk(handle);provider=CompatibleProvider(client=sdk,base_url='https://test.invalid',model='test',instructions='')
            try:
                with self.assertRaises(ProviderError) as cm:[x async for x in provider.stream(MESSAGES)]
                self.assertEqual(cm.exception.code,'UPSTREAM_UNAVAILABLE')
            finally:await provider.close()

    async def test_incomplete_malformed_and_in_band_failures(self):
        cases=[([chunk('partial')],False),([chunk('partial',finish='length')],True),
               ([chunk(finish='tool_calls')],True),([chunk(finish='content_filter')],True),
               ([chunk(error={'code':429,'message':DETAIL+KEY},finish='error')],True),
               ([chunk(finish='stop'),chunk('after-terminal')],True),
               ([chunk(content=[{'type':'image_url','image_url':'private'}])],True)]
        for events,done in cases:
            response=httpx.Response(200,headers={'content-type':'text/event-stream'},content=sse(events,done))
            sdk=self.sdk(lambda req:response)
            provider=CompatibleProvider(client=sdk,base_url='https://test.invalid',model='test',instructions='')
            try:
                with self.assertRaises(ProviderError) as cm:[x async for x in provider.stream(MESSAGES)]
                self.assertNotIn(DETAIL,str(cm.exception));self.assertTrue(response.is_closed)
                if any('error' in event and event['error'].get('code')==429 for event in events):
                    self.assertEqual(cm.exception.code,'UPSTREAM_RATE_LIMIT')
            finally:await provider.close()
        response=httpx.Response(200,headers={'content-type':'text/event-stream'},content='data: {broken\n\n')
        sdk=self.sdk(lambda req:response);provider=CompatibleProvider(client=sdk,base_url='https://test.invalid',model='test',instructions='')
        try:
            with self.assertRaises(ProviderError):[x async for x in provider.stream(MESSAGES)]
            self.assertTrue(response.is_closed)
        finally:await provider.close()

    async def test_mistral_text_blocks_and_reasoning_ignored(self):
        response=httpx.Response(200,headers={'content-type':'text/event-stream'},content=sse([
            chunk(content=[{'type':'text','text':'visible'}]),
            {'id':'test','created':0,'object':'chat.completion.chunk','model':'test','choices':[{'index':0,'delta':{'reasoning_content':'private-thought'},'finish_reason':'stop'}]}]))
        sdk=self.sdk(lambda req:response);provider=CompatibleProvider(client=sdk,base_url='https://test.invalid',model='test',instructions='')
        try:self.assertEqual(''.join([x async for x in provider.stream(MESSAGES)]),'visible')
        finally:await provider.close()

    async def test_mistral_documented_thinking_transition_and_text_stream(self):
        thinking = {'type':'thinking','thinking':[{'type':'text','text':DETAIL+KEY}]}
        for events, valid in (
            ([chunk(content=[thinking]),
              chunk(content=[thinking, {'type':'text','text':'visible'}]),
              chunk(' answer'), chunk(finish='stop')], True),
            ([chunk(content=[{'type':'thinking','thinking':'invalid'}]), chunk(finish='stop')], False),
            ([chunk(content=[{'type':'thinking','thinking':[{'type':'image_url'}]}]), chunk(finish='stop')], False),
            ([chunk(finish='stop'),chunk(content=[thinking])], False)):
            requests=[]
            response=httpx.Response(200,headers={'content-type':'text/event-stream'},content=sse(events))
            def handle(request):
                requests.append(request)
                body=json.loads(request.content)
                self.assertEqual(body['reasoning_effort'],'high')
                self.assertEqual(body['model'],'mistral-small-latest')
                return response
            sdk=self.sdk(handle,PRESETS['mistral'][0])
            with patch('ai4dos.compatible_provider.make_client',return_value=sdk):
                provider=build_provider(Settings(devices={'d':'d'*32},provider='mistral',
                    model='mistral-small-latest',api_key=KEY,reasoning='high'))
            try:
                if valid:
                    self.assertEqual(''.join([x async for x in provider.stream(MESSAGES)]),'visible answer')
                else:
                    with self.assertRaises(ProviderError) as caught:
                        [x async for x in provider.stream(MESSAGES)]
                    self.assertNotIn(KEY,str(caught.exception))
                self.assertEqual(len(requests),1)
                self.assertTrue(response.is_closed)
            finally:await provider.close()
        response=httpx.Response(200,headers={'content-type':'text/event-stream'},
            content=sse([chunk(content=[thinking]),chunk(finish='stop')]))
        provider=CompatibleProvider(client=self.sdk(lambda req:response),base_url='https://test.invalid',
                                    model='test',instructions='',label='AI')
        try:
            with self.assertRaises(ProviderError):[x async for x in provider.stream(MESSAGES)]
        finally:await provider.close()

    async def test_early_generator_close_closes_sdk_stream(self):
        for mode in ('chat','responses'):
            events=[chunk('one'),chunk('two'),chunk(finish='stop')] if mode=='chat' else [
                {'type':'response.output_text.delta','delta':'one'},{'type':'response.output_text.delta','delta':'two'},
                {'type':'response.completed','response':{'status':'completed'}}]
            response=httpx.Response(200,headers={'content-type':'text/event-stream'},content=sse(events))
            sdk=self.sdk(lambda req:response)
            provider=CompatibleProvider(client=sdk,base_url='https://test.invalid',model='test',instructions='') if mode=='chat' else OpenAIProvider(client=sdk,model='test',instructions='')
            stream=provider.stream(MESSAGES)
            try:
                self.assertEqual(await stream.__anext__(),'one');await stream.aclose();self.assertTrue(response.is_closed)
            finally:await provider.close()

    async def test_gateway_neutral_errors_no_raw_body_or_logs(self):
        for status,expected in ((401,'UPSTREAM_AUTH'),(404,'UPSTREAM_MODEL'),(429,'UPSTREAM_RATE_LIMIT'),(503,'UPSTREAM_UNAVAILABLE'),(500,'UPSTREAM')):
            sdk=self.sdk(lambda req:httpx.Response(status,json={'error':{'message':DETAIL+KEY}}))
            provider=CompatibleProvider(client=sdk,base_url='https://test.invalid',model='test',instructions='')
            secret=secrets.token_hex(32);g=Gateway(Settings(port=0,devices={'d':secret}),provider);server=await g.start()
            r,w=await asyncio.open_connection('127.0.0.1',server.sockets[0].getsockname()[1])
            async def read():return (await asyncio.wait_for(r.readline(),3)).decode().strip()
            async def send(text):w.write((text+'\r\n').encode());await w.drain()
            try:
                await read();await send('HELLO d');nonce=(await read()).split()[1]
                await send('AUTH '+hmac.new(secret.encode(),nonce.encode(),hashlib.sha256).hexdigest());await read()
                await send('NEW');await read()
                with self.assertLogs('ai4dos',level='WARNING') as captured:
                    await send('MSG test');self.assertEqual(await read(),'BEGIN');wire=await read()
                self.assertTrue(wire.startswith('ERROR '+expected+' '),wire)
                self.assertNotIn(KEY,wire+str(captured.output));self.assertNotIn(DETAIL,wire+str(captured.output))
                await send('QUIT');self.assertEqual(await read(),'OK BYE')
            finally:w.close();await w.wait_closed();server.close();await server.wait_closed();await g.close()

    async def test_real_local_http_compatible_gateway_auth_resume_history(self):
        # Real socket HTTP/SSE API behind SDK + real gateway TCP; synthetic keys only.
        for mode in ('chat','responses'):
            requests=[]
            async def http_handler(reader, writer):
                try:
                    header=await reader.readuntil(b"\r\n\r\n")
                    length=int(next(row.split(b":",1)[1] for row in header.split(b"\r\n") if row.lower().startswith(b"content-length:")))
                    body=json.loads(await reader.readexactly(length));requests.append(body)
                    expected='/v1/chat/completions' if mode=='chat' else '/v1/responses'
                    self.assertTrue(header.split(b"\r\n")[0].startswith(('POST '+expected+' ').encode()))
                    text='local-first' if len(requests)==1 else 'local-resumed'
                    events=[chunk(text),chunk(finish='stop')] if mode=='chat' else [
                        {'type':'response.output_text.delta','delta':text},
                        {'type':'response.completed','response':{'status':'completed'}}]
                    payload=sse(events).encode()
                    writer.write(b'HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nConnection: close\r\nContent-Length: '+str(len(payload)).encode()+b'\r\n\r\n'+payload)
                    await writer.drain()
                finally:writer.close();await writer.wait_closed()
            http=await asyncio.start_server(http_handler,'127.0.0.1',0)
            base='http://127.0.0.1:'+str(http.sockets[0].getsockname()[1])+'/v1'
            secret=secrets.token_hex(32)
            settings=Settings(port=0,devices={'d':secret},provider='openai-compatible',api_key=KEY,model='local-test',base_url=base,api_mode=mode)
            g=Gateway(settings,build_provider(settings));server=await g.start();writers=[]
            async def connect():
                r,w=await asyncio.open_connection('127.0.0.1',server.sockets[0].getsockname()[1]);writers.append(w)
                async def read():return (await asyncio.wait_for(r.readline(),3)).decode().strip()
                async def send(text):w.write((text+'\r\n').encode());await w.drain()
                await read();await send('HELLO d');nonce=(await read()).split()[1]
                await send('AUTH '+hmac.new(secret.encode(),nonce.encode(),hashlib.sha256).hexdigest());self.assertEqual(await read(),'OK AUTH')
                return read,send
            try:
                read,send=await connect();await send('NEW');sid=(await read()).split()[1]
                for i in range(2):
                    if i:
                        writers[-1].close();await writers[-1].wait_closed()
                        while g.active:await asyncio.sleep(.01)
                        read,send=await connect();await send('RESUME '+sid);self.assertEqual(await read(),'OK RESUME')
                    await send('MSG '+('first' if not i else 'second'))
                    self.assertEqual(await read(),'BEGIN');self.assertEqual(await read(),'DATA '+('local-first' if not i else 'local-resumed'));self.assertEqual(await read(),'END')
                history=requests[-1]['messages' if mode=='chat' else 'input']
                self.assertEqual([m['role'] for m in history if m['role']!='system'],['user','assistant','user'])
                self.assertEqual(history[-2]['content'],'local-first');self.assertEqual(len(requests),2)
                await send('QUIT');self.assertEqual(await read(),'OK BYE')
            finally:
                for w in writers:w.close();await w.wait_closed()
                server.close();await server.wait_closed();await g.close();http.close();await http.wait_closed()


class ConfigContracts(unittest.TestCase):
    def test_quickstart_file_and_existing_json(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);cfg=p/'gateway.json';provider=p/'provider.cfg'
            cfg.write_text(json.dumps({'devices':{'d':'d'*32},'provider_config':'provider.cfg','provider':'openai','api_key':KEY}))
            provider.write_text('PROVIDER=openrouter\nMODEL=\nAPI_KEY=\n')
            s=Settings.load(cfg);self.assertEqual(s.provider,'openrouter');self.assertEqual(s.model,'openrouter/free');self.assertEqual(s.api_key,'')
            with patch.dict(os.environ,{'OPENROUTER_API_KEY':KEY},clear=True),patch('ai4dos.compatible_provider.make_client') as factory:
                build_provider(s);factory.assert_called_once_with(KEY,PRESETS['openrouter'][0])
            cfg.write_text(json.dumps({'devices':{'d':'d'*32},'provider':'mock'}));self.assertEqual(Settings.load(cfg).provider,'mock')
            provider.write_text('API_KEY=x\nAPI_KEY=y');cfg.write_text(json.dumps({'devices':{'d':'d'*32},'provider_config':'provider.cfg'}))
            with self.assertRaises(ValueError):Settings.load(cfg)

    def test_key_file_runtime_and_repr_redaction(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);(p/'key.local').write_text(KEY)
            (p/'provider.cfg').write_text('PROVIDER=mistral\nMODEL=test\nAPI_KEY_FILE=key.local\n')
            (p/'gateway.json').write_text(json.dumps({'devices':{'d':'d'*32},'provider_config':'provider.cfg'}))
            s=Settings.load(p/'gateway.json')
            self.assertNotIn(KEY,repr(s))
            with patch('ai4dos.compatible_provider.make_client') as factory:
                build_provider(s);factory.assert_called_once_with(KEY,PRESETS['mistral'][0])
            self.assertNotIn(KEY,repr(Settings(devices={'d':'d'*32},api_key=KEY)))

    def test_invalid_config_and_missing_key(self):
        for values in ({'provider':'mistral'},{'provider':'openai-compatible','model':'m'},
                       {'provider':'openai-compatible','model':'m','base_url':'https://key@host/v1'},
                       {'provider':'openai-compatible','model':'m','base_url':'https://host/v1?api_key=private'},
                       {'provider':'openai-compatible','model':'m','base_url':'file:///private'},
                       {'provider':'mistral','model':'m','api_mode':'responses'},
                       {'provider':'openai','model':'m','base_url':'https://other/v1'},
                       {'api_key':KEY,'api_key_file':'key'}):
            with self.subTest(values=values),self.assertRaises(ValueError):Settings(devices={'d':'d'*32},**values)
        with patch.dict(os.environ,{},clear=True),self.assertRaises(ValueError):
            build_provider(Settings(devices={'d':'d'*32},provider='openrouter'))
