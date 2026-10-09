"""Migrated Georgi capabilities and shared quality, entirely offline transports."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import httpx
from openai import AsyncOpenAI
from ai4dos.config import Settings, build_provider, nvidia_options
from ai4dos.gemini_provider import GeminiProvider
from ai4dos.provider import DOS_CAPABILITIES, ProviderError
from ai4dos.session import Message, Role

KEY = 'synthetic-contract-key'
MESSAGES = [Message(Role.ROLE_USER, 'one'), Message(Role.ROLE_AI, 'two'),
            Message(Role.ROLE_SYSTEM, 'technical note')]


def native(text=None, finish=None, **extra):
    candidate = {'index': 0, **extra}
    if text is not None:
        candidate['content'] = {'role': 'model', 'parts': [{'text': text}]}
    if finish:
        candidate['finishReason'] = finish
    return {'candidates': [candidate]}


def sse(events):
    return ''.join('data: ' + json.dumps(x) + '\n\n' for x in events)


class ProviderRegressions(unittest.IsolatedAsyncioTestCase):
    def settings(self, **values):
        return Settings(devices={'d': 'd'*32}, model='contract-model', api_key=KEY, **values)

    async def test_gemini_native_roles_thought_temperature_thinking_filter_and_limits(self):
        requests = []; responses = []
        def handle(request):
            requests.append(request)
            response = httpx.Response(200, headers={'content-type': 'text/event-stream'}, content=sse([
                native(content={'parts': [{'text':'hidden','thought':True}, {'text':'hello<|fim_'}]}),
                native('suffix|> world', 'STOP'), {'usageMetadata': {'candidatesTokenCount': 4}}]))
            responses.append(response)
            return response
        client = httpx.AsyncClient(transport=httpx.MockTransport(handle), trust_env=False)
        with patch('ai4dos.gemini_provider.make_http_client', return_value=client):
            provider = build_provider(self.settings(provider='gemini', thinking_level='high', temperature=0.25, max_output_tokens=333))
        try:
            self.assertIsInstance(provider, GeminiProvider)
            self.assertEqual(''.join([p async for p in provider.stream(MESSAGES)]), 'hello world')
            request = requests[0]; body = json.loads(request.content)
            self.assertEqual(str(request.url), GeminiProvider.API_BASE+'/contract-model:streamGenerateContent?alt=sse')
            self.assertEqual(request.headers['x-goog-api-key'], KEY)
            self.assertNotIn('authorization', request.headers)
            self.assertEqual(body['contents'], [{'role':'user','parts':[{'text':'one'}]}, {'role':'model','parts':[{'text':'two'}]}])
            self.assertEqual(body['generationConfig'], {'temperature':0.25,'maxOutputTokens':333,'thinkingConfig':{'thinkingLevel':'HIGH'}})
            self.assertEqual(body['systemInstruction']['parts'][0]['text'], DOS_CAPABILITIES+'\n\nAnswer clearly in plain text.\n\ntechnical note')
            self.assertTrue(responses[0].is_closed)
        finally:
            await provider.close()
        self.assertTrue(client.is_closed)

    async def test_gemini_release_model_exact_native_path_and_404(self):
        requests = []
        def handle(request):
            requests.append(request)
            self.assertEqual(str(request.url),
                'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse')
            self.assertEqual(request.method, 'POST')
            self.assertEqual(request.headers['x-goog-api-key'], KEY)
            self.assertEqual(json.loads(request.content)['generationConfig']['thinkingConfig'],
                             {'thinkingBudget': 0})
            return httpx.Response(404, json={'error':{'code':404,'status':'NOT_FOUND','message':KEY}})
        client = httpx.AsyncClient(transport=httpx.MockTransport(handle), trust_env=False)
        with patch('ai4dos.gemini_provider.make_http_client', return_value=client):
            provider = build_provider(Settings(devices={'d':'synthetic-device-key'},
                provider='gemini', model='gemini-2.5-flash', api_key=KEY, reasoning='none'))
        try:
            with self.assertRaises(ProviderError) as caught:
                [part async for part in provider.stream(MESSAGES)]
            self.assertEqual(caught.exception.code, 'UPSTREAM_MODEL')
            self.assertNotIn(KEY, str(caught.exception))
            self.assertEqual(len(requests), 1)
        finally:
            await provider.close()
        self.assertTrue(client.is_closed)

    async def test_gemini_thinking_budget_and_generation_default(self):
        for model, settings, expected in (
            ('gemini-3.8-flash', {}, None),
            ('gemini-2.5-flash', {'thinking_budget':0}, {'thinkingBudget':0}),
            ('gemini-2.5-flash', {'thinking_budget':-1}, {'thinkingBudget':-1}),
            ('gemini-2.0-flash', {}, None)):
            requests = []
            def handle(request):
                requests.append(json.loads(request.content))
                return httpx.Response(200,content=sse([native('okay','STOP')]))
            client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
            provider = GeminiProvider(api_key=KEY,model=model,instructions='',client=client,**settings)
            try:
                self.assertEqual(''.join([x async for x in provider.stream(MESSAGES)]),'okay')
                self.assertEqual(requests[0]['generationConfig'].get('thinkingConfig'),expected)
                self.assertEqual(requests[0]['generationConfig']['temperature'],0.5)
            finally: await provider.close()

    async def test_gemini_incomplete_blocked_errors_nontext_and_cleanup(self):
        cases = [([native('partial')], 'UPSTREAM'), ([native('partial','MAX_TOKENS')], 'UPSTREAM'),
                 ([native(finish='SAFETY')], 'UPSTREAM'), ([{'promptFeedback':{'blockReason':'SAFETY'}}], 'UPSTREAM'),
                 ([{'error':{'code':429,'message':KEY}}], 'UPSTREAM_RATE_LIMIT'),
                 ([native('ok','STOP'),native('after')], 'UPSTREAM'),
                 ([native('ok','STOP'),native(finish='STOP')], 'UPSTREAM'),
                 ([native(content={'parts':[{'functionCall':{'name':'not-supported'}}]})], 'UPSTREAM'),
                 ([{'candidates':[{'index':1,'finishReason':'STOP'}]}], 'UPSTREAM')]
        for events, code in cases:
            with self.subTest(events=events):
                response = httpx.Response(200,content=sse(events))
                client = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: response))
                provider = GeminiProvider(api_key=KEY,model='test',instructions='',client=client)
                try:
                    with self.assertRaises(ProviderError) as cm: [x async for x in provider.stream(MESSAGES)]
                    self.assertEqual(cm.exception.code,code)
                    self.assertNotIn(KEY,str(cm.exception));self.assertTrue(response.is_closed)
                finally: await provider.close()

    async def test_gemini_http_network_malformed_and_early_close(self):
        for status, code in ((401,'UPSTREAM_AUTH'),(403,'UPSTREAM_AUTH'),(404,'UPSTREAM_MODEL'),(429,'UPSTREAM_RATE_LIMIT'),(503,'UPSTREAM_UNAVAILABLE'),(500,'UPSTREAM')):
            response = httpx.Response(status,json={'error':{'message':KEY}})
            requests = []
            def handle(req):requests.append(req);return response
            client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
            provider = GeminiProvider(api_key=KEY,model='test',instructions='',client=client)
            try:
                with self.assertRaises(ProviderError) as cm:[x async for x in provider.stream(MESSAGES)]
                self.assertEqual(cm.exception.code,code);self.assertNotIn(KEY,str(cm.exception))
                self.assertEqual(len(requests),1);self.assertTrue(response.is_closed)
            finally: await provider.close()
        for error in (httpx.ConnectError,httpx.ReadTimeout):
            def handle(req):raise error(KEY,request=req)
            client=httpx.AsyncClient(transport=httpx.MockTransport(handle))
            provider=GeminiProvider(api_key=KEY,model='test',instructions='',client=client)
            try:
                with self.assertRaises(ProviderError) as cm:[x async for x in provider.stream(MESSAGES)]
                self.assertEqual(cm.exception.code,'UPSTREAM_UNAVAILABLE')
            finally:await provider.close()
        response=httpx.Response(200,content='data: {invalid\n\n')
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda req:response))
        provider=GeminiProvider(api_key=KEY,model='test',instructions='',client=client)
        try:
            with self.assertRaises(ProviderError):[x async for x in provider.stream(MESSAGES)]
            self.assertTrue(response.is_closed)
        finally:await provider.close()
        response=httpx.Response(200,content=sse([native('one'),native('two','STOP')]))
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda req:response))
        provider=GeminiProvider(api_key=KEY,model='test',instructions='',client=client)
        stream=provider.stream(MESSAGES)
        try:
            self.assertEqual(await stream.__anext__(),'one');await stream.aclose()
            self.assertTrue(response.is_closed)
        finally:await provider.close()

    async def test_every_sdk_provider_shared_capabilities_limits_and_nvidia_options(self):
        cases = [('openai','contract-model',{},None),('openai','gpt-6-luna',{}, {'effort':'none'}),
                 ('openai','gpt-6-luna',{'reasoning_effort':'low'}, {'effort':'low'}),
                 ('nvidia','deepseek-ai/deepseek-v4.1-flash',{}, {}),
                 ('nvidia','z-ai/glm-5.3',{}, {'chat_template_kwargs':{'clear_thinking':True}}),
                 ('nvidia','contract-model',{}, {}),
                 ('nvidia','z-ai/glm-5.3',{'reasoning_effort':'high','clear_thinking':False,'enable_thinking':True},
                  {'reasoning_effort':'high','chat_template_kwargs':{'clear_thinking':False,'enable_thinking':True}}),
                 ('openrouter','contract-model',{},None),('mistral','contract-model',{},None),
                 ('openai-compatible','contract-model',{},None),
                 ('openai-compatible','contract-model',{'api_mode':'responses','reasoning_effort':'none'}, {'effort':'none'})]
        for name, model, options, expected in cases:
            with self.subTest(provider=name,model=model,options=options):
                responses=[];requests=[]
                mode=options.get('api_mode', 'responses' if name=='openai' else 'chat')
                def handle(req):
                    requests.append(json.loads(req.content))
                    events=[{'type':'response.output_text.delta','delta':'okay'}, {'type':'response.completed','response':{'status':'completed'}}] if mode=='responses' else [
                        {'id':'x','created':0,'object':'chat.completion.chunk','model':model,
                         'choices':[{'index':0,'delta':{'content':'okay'},'finish_reason':'stop'}]}]
                    response=httpx.Response(200,headers={'content-type':'text/event-stream'},content=sse(events))
                    responses.append(response);return response
                sdk=AsyncOpenAI(api_key=KEY,base_url='https://test.invalid/v1',max_retries=0,
                                http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)))
                module='openai_provider' if mode=='responses' else 'compatible_provider'
                with patch('ai4dos.'+module+'.make_client',return_value=sdk):
                    values=dict(devices={'d':'d'*32},provider=name,model=model,api_key=KEY,max_output_tokens=321,**options)
                    if name=='openai-compatible':values['base_url']='https://test.invalid/v1'
                    provider=build_provider(Settings(**values))
                try:
                    self.assertEqual(''.join([x async for x in provider.stream(MESSAGES)]),'okay')
                    body=requests[0]
                    self.assertEqual(body['max_output_tokens' if mode=='responses' else 'max_tokens'],321)
                    if mode=='responses':
                        self.assertIn(DOS_CAPABILITIES,body['instructions']);self.assertFalse(body['store'])
                        self.assertEqual(body.get('reasoning'),expected)
                    else:
                        self.assertIn(DOS_CAPABILITIES,body['messages'][0]['content'])
                        self.assertEqual([m['role'] for m in body['messages'][1:]],['user','assistant','system'])
                        if name=='nvidia':
                            self.assertEqual({k:body[k] for k in expected},expected)
                        else:
                            self.assertNotIn('reasoning_effort',body);self.assertNotIn('chat_template_kwargs',body)
                            if name == 'openrouter':self.assertEqual(body['reasoning'],{'enabled':False})
                    self.assertTrue(responses[0].is_closed)
                finally:await provider.close()
                self.assertTrue(sdk.is_closed)

    async def test_reasoning_none_default_mapping_and_explicit_opt_in(self):
        from ai4dos.config import responses_reasoning, chat_reasoning, gemini_thinking
        cases = [
            ({'provider':'openai','model':'gpt-6-luna'}, 'none'),
            ({'provider':'openai','model':'gpt-5.1'}, 'none'),
            ({'provider':'openai','model':'gpt-6-astra'}, None),
            ({'provider':'openai','model':'gpt-6.1-sol'}, None),
            ({'provider':'openai','model':'gpt-4.1'}, None),
            ({'provider':'openai','model':'gpt-6-luna','reasoning':'high'}, 'high'),
            ({'provider':'openai-compatible','model':'gpt-6-luna','base_url':'http://localhost/v1','api_mode':'responses'}, None)]
        for values, expected in cases:
            settings=Settings(devices={'d':'d'*32},**values)
            self.assertEqual(settings.reasoning,'none' if 'reasoning' not in values else values['reasoning'])
            self.assertEqual(responses_reasoning(settings),expected)
        for model, expected in (('gemini-2.5-flash',(None,0)),('gemini-2.5-flash-lite',(None,0)),
                                ('gemini-2.5-pro',(None,None)),('gemini-3.8-flash',(None,None)),('unknown',(None,None))):
            settings=Settings(devices={'d':'d'*32},provider='gemini',model=model,api_key=KEY)
            self.assertEqual(gemini_thinking(settings),expected)
            requests=[]
            def handle(req):
                requests.append(json.loads(req.content))
                return httpx.Response(200,content=sse([native('okay','STOP')]))
            client=httpx.AsyncClient(transport=httpx.MockTransport(handle))
            with patch('ai4dos.gemini_provider.make_http_client',return_value=client):provider=build_provider(settings)
            try:
                self.assertEqual(''.join([x async for x in provider.stream(MESSAGES)]),'okay')
                self.assertEqual(requests[0]['generationConfig'].get('thinkingConfig'),{'thinkingBudget':0} if expected[1]==0 else None)
            finally:await provider.close()
        for values, expected in (
            ({'provider':'openrouter','model':'openrouter/free'},{'reasoning':{'enabled':False}}),
            ({'provider':'openrouter','model':'openrouter/free','reasoning':'high'},{'reasoning':{'effort':'high'}}),
            ({'provider':'mistral','model':'mistral-small-latest'},{'reasoning_effort':'none'}),
            ({'provider':'mistral','model':'mistral-medium-3-5'},{'reasoning_effort':'none'}),
            ({'provider':'mistral','model':'mistral-small-latest','reasoning':'high'},{'reasoning_effort':'high'}),
            ({'provider':'mistral','model':'zai-glm-5-3'},{}),
            ({'provider':'mistral','model':'future-mistral-model','reasoning':'high'},{'reasoning_effort':'high'}),
            ({'provider':'mistral','model':'future-mistral-model','reasoning_effort':'low'},{'reasoning_effort':'low'}),
            ({'provider':'mistral','model':'future-mistral-model','reasoning_effort':'none'},{'reasoning_effort':'none'}),
            ({'provider':'nvidia','model':'nvidia/nemotron-3-super-120b-a12b'},{'chat_template_kwargs':{'enable_thinking':False}}),
            ({'provider':'nvidia','model':'deepseek-ai/deepseek-v4.1-flash'},{}),
            ({'provider':'nvidia','model':'z-ai/glm-5.3'},{'chat_template_kwargs':{'clear_thinking':True}}),
            ({'provider':'openai-compatible','model':'unknown','base_url':'http://localhost/v1'},{})):
            settings=Settings(devices={'d':'d'*32},api_key=KEY,**values)
            self.assertEqual(chat_reasoning(settings),expected)
            requests=[]
            def handle(req):
                requests.append(json.loads(req.content))
                return httpx.Response(200,headers={'content-type':'text/event-stream'},content=sse([
                    {'id':'x','created':0,'object':'chat.completion.chunk','model':'test',
                     'choices':[{'index':0,'delta':{'content':'okay'},'finish_reason':'stop'}]}]))
            sdk=AsyncOpenAI(api_key=KEY,max_retries=0,http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)))
            with patch('ai4dos.compatible_provider.make_client',return_value=sdk):provider=build_provider(settings)
            try:
                self.assertEqual(''.join([x async for x in provider.stream(MESSAGES)]),'okay')
                body=requests[0]
                self.assertEqual({k:v for k,v in body.items() if k in {'reasoning','reasoning_effort','chat_template_kwargs'}},expected)
            finally:await provider.close()
        for model in ('mistral-small-latest','mistral-medium-3-5'):
            with self.subTest(model=model),self.assertRaises(ValueError):
                Settings(devices={'d':'d'*32},provider='mistral',model=model,reasoning='low')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'provider.cfg').write_text('PROVIDER=openai\nMODEL=gpt-6-luna\nREASONING=none\n')
            (root/'gateway.json').write_text(json.dumps({'devices':{'d':'d'*32},'provider_config':'provider.cfg'}))
            self.assertEqual(Settings.load(root/'gateway.json').reasoning,'none')

    async def test_openai_terminal_consistency_and_cleanup(self):
        from ai4dos.openai_provider import OpenAIProvider
        completed = {'type':'response.completed','response':{'status':'completed'}}
        for events in ([completed, {'type':'response.output_text.delta','delta':'after'}],
                       [completed, completed],
                       [{'type':'response.completed','response':{'status':'incomplete'}}]):
            response=httpx.Response(200,headers={'content-type':'text/event-stream'},content=sse(events))
            sdk=AsyncOpenAI(api_key=KEY,max_retries=0,
                            http_client=httpx.AsyncClient(transport=httpx.MockTransport(lambda req:response)))
            provider=OpenAIProvider(client=sdk,model='test',instructions='')
            try:
                with self.assertRaises(ProviderError):[x async for x in provider.stream(MESSAGES)]
                self.assertTrue(response.is_closed)
            finally:await provider.close()

    async def test_responses_stream_errors_preserve_safe_error_categories(self):
        from ai4dos.openai_provider import OpenAIProvider
        cases = [('invalid_api_key', 'UPSTREAM_AUTH'),
                 ('model_not_found', 'UPSTREAM_MODEL'),
                 ('rate_limit_exceeded', 'UPSTREAM_RATE_LIMIT'),
                 ('service_unavailable', 'UPSTREAM_UNAVAILABLE'),
                 ('server_error', 'UPSTREAM'), (None, 'UPSTREAM')]
        for mode in ('error', 'response.failed'):
            for code, expected in cases:
                with self.subTest(mode=mode, code=code):
                    error = {'code': code, 'message': KEY, 'param': None}
                    event = dict(type='error', **error) if mode == 'error' else {
                        'type': mode, 'response': {'status': 'failed', 'error': error}}
                    requests = []
                    response = httpx.Response(200, headers={'content-type':'text/event-stream'},
                                              content=sse([event]))
                    def handle(request):
                        requests.append(request)
                        return response
                    sdk = AsyncOpenAI(api_key=KEY, max_retries=0,
                        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)))
                    provider = OpenAIProvider(client=sdk, model='arbitrary-model', instructions='')
                    try:
                        with self.assertRaises(ProviderError) as caught:
                            [part async for part in provider.stream(MESSAGES)]
                        self.assertEqual(caught.exception.code, expected)
                        self.assertNotIn(KEY, str(caught.exception))
                        self.assertEqual(len(requests), 1)
                        self.assertTrue(response.is_closed)
                    finally:
                        await provider.close()

    async def test_native_multiline_sse_and_final_record(self):
        event=json.dumps(native('visible','STOP'),indent=2)
        body=': comment\n'+'\n'.join('data: '+line for line in event.splitlines())
        response=httpx.Response(200,content=body)
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda req:response))
        provider=GeminiProvider(api_key=KEY,model='test',instructions='',client=client)
        try:
            self.assertEqual(''.join([x async for x in provider.stream(MESSAGES)]),'visible')
            self.assertTrue(response.is_closed)
        finally:await provider.close()

    def test_config_types_overrides_validation_and_device_independence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); cfg=root/'gateway.json'; provider=root/'provider.cfg'
            cfg.write_text(json.dumps({'devices':{'d':'d'*32},'max_output_tokens':777,'provider_config':'provider.cfg'}))
            provider.write_text('PROVIDER=gemini\nMODEL=gemini-3.8-flash\nTHINKING_LEVEL=high\nTEMPERATURE=0.25\n')
            settings=Settings.load(cfg);self.assertEqual(settings.max_output_tokens,777)
            provider.write_text(provider.read_text()+'MAX_OUTPUT_TOKENS=123\n')
            self.assertEqual(Settings.load(cfg).max_output_tokens,123)
            provider.write_text('PROVIDER=nvidia\nMODEL=z-ai/glm-5.3\nREASONING_EFFORT=low\nENABLE_THINKING=false\nCLEAR_THINKING=true\n')
            settings=Settings.load(cfg)
            other=Settings(devices={'another':'x'*32},provider='nvidia',model=settings.model)
            self.assertEqual(nvidia_options(settings), {**nvidia_options(other),'reasoning_effort':'low','chat_template_kwargs':{'clear_thinking':True,'enable_thinking':False}})
            self.assertEqual(nvidia_options(other),nvidia_options(Settings(devices={'public':'y'*32},provider='nvidia',model=other.model)))
        for values in ({'max_output_tokens':0},{'max_output_tokens':True},{'max_output_tokens':1.5},
                       {'temperature':float('nan')},{'temperature':3}, {'thinking_level':'wrong'},
                       {'thinking_level':'low','thinking_budget':0},{'thinking_budget':-2},
                       {'enable_thinking':'false'}, {'clear_thinking':True}):
            with self.subTest(values=values),self.assertRaises(ValueError):
                Settings(devices={'d':'d'*32},provider='gemini',model='test',**values)
