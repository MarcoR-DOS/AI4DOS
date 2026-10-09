"""Actual provider construction -> gateway -> native client, without API calls."""
import asyncio
import hashlib
import hmac
from pathlib import Path
import tempfile
import unittest
from ai4dos.config import Settings, build_provider
from ai4dos.provider import DOS_CAPABILITIES, MockProvider
from ai4dos.server import Gateway

ROOT = Path(__file__).resolve().parents[1]
def connection_notices(language):
    return ('System: Verbinde mit Gateway...\nSystem: Verbunden. Du kannst jetzt chatten.\n'
            if language=='de' else
            'System: Connecting to gateway...\nSystem: Connected. You can start chatting.\n')

LABELS = {'openai':'ChatGPT','anthropic':'Claude','gemini':'Gemini',
          'mistral':'Mistral','nvidia':'NVIDIA','openrouter':'OpenRouter',
          'openai-compatible':'','mock':''}


def provider_for(name):
    settings = Settings(devices={'d':'offline-device-key'}, provider=name, model='offline-test-model', api_key='offline-test-key',
                        base_url='http://127.0.0.1:1/v1' if name=='openai-compatible' else '',
                        api_mode='')
    provider = build_provider(settings)
    # Replace only the stream, preserving real construction, instructions and label.
    provider.stream = MockProvider().stream
    return provider


class ProviderLabels(unittest.IsolatedAsyncioTestCase):
    async def test_every_provider_and_fallback_display_en_de(self):
        for name, label in LABELS.items():
            provider = provider_for(name)
            if name != 'mock':
                self.assertIn(DOS_CAPABILITIES, provider.instructions)
                self.assertEqual(provider.instructions.count("Respond in the language used by the user unless the user asks for another language."), 1)
            gateway = Gateway(Settings(port=0, devices={'d':'offline-device-key'}), provider)
            listener = await gateway.start()
            try:
                for language in ('en','de'):
                    with self.subTest(provider=name, language=language), tempfile.TemporaryDirectory() as folder:
                        cfg = Path(folder)/'AI4DOS.CFG'
                        cfg.write_text('SERVER=127.0.0.1\nPORT=%s\nDEVICE=d\nSECRET=offline-device-key\nLANGUAGE=%s\n' %
                                       (listener.sockets[0].getsockname()[1], language))
                        proc = await asyncio.create_subprocess_exec(str(ROOT/'client/build/ai4dos-host'),
                            str(cfg), 'hello', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                        out, err = await asyncio.wait_for(proc.communicate(), 5)
                        self.assertEqual(proc.returncode, 0, err)
                        self.assertEqual(out, (connection_notices(language)+(label or ('KI' if language=='de' else 'AI'))+
                                              ': Test reply: hello\n').encode())
            finally:
                listener.close(); await listener.wait_closed(); await gateway.close()

    async def test_legacy_02_gateway_fallback_en_de(self):
        class LegacyGateway(Gateway):
            async def write(self, writer, line):
                if line == 'OK AI4DOS/0.3 UTF-8': line = 'OK AI4DOS/0.2 UTF-8'
                if line.startswith('BEGIN '): line = 'BEGIN'
                await super().write(writer, line)
        provider = MockProvider(); provider.label = 'Claude'
        gateway = LegacyGateway(Settings(port=0, devices={'d':'offline-device-key'}), provider)
        listener = await gateway.start()
        try:
            for language in ('en','de'):
                with self.subTest(language=language), tempfile.TemporaryDirectory() as folder:
                    cfg = Path(folder)/'AI4DOS.CFG'
                    cfg.write_text('SERVER=127.0.0.1\nPORT=%s\nDEVICE=d\nSECRET=offline-device-key\nLANGUAGE=%s\n' %
                                   (listener.sockets[0].getsockname()[1], language))
                    proc = await asyncio.create_subprocess_exec(str(ROOT/'client/build/ai4dos-host'),
                        str(cfg), 'hello', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    out, err = await asyncio.wait_for(proc.communicate(), 5)
                    self.assertEqual(proc.returncode,0,err)
                    self.assertEqual(out, (connection_notices(language)+('KI' if language=='de' else 'AI')+': Test reply: hello\n').encode())
        finally:
            listener.close(); await listener.wait_closed(); await gateway.close()

    async def test_resume_reconnect_and_changed_label_do_not_change_session(self):
        provider = MockProvider(); provider.label = 'Claude'
        gateway = Gateway(Settings(port=0, devices={'d':'offline-device-key'}), provider)
        listener = await gateway.start()
        async def connect():
            r, w = await asyncio.open_connection('127.0.0.1', listener.sockets[0].getsockname()[1])
            async def send(text):
                w.write((text+'\r\n').encode()); await w.drain()
            async def read():
                return (await asyncio.wait_for(r.readline(), 3)).decode().strip()
            self.assertEqual(await read(), 'OK AI4DOS/0.3 UTF-8')
            await send('HELLO d'); challenge = (await read()).split()[1]
            await send('AUTH '+hmac.new(b'offline-device-key', challenge.encode(), hashlib.sha256).hexdigest())
            self.assertEqual(await read(), 'OK AUTH')
            return r, w, send, read
        async def reply(send, read, label):
            await send('MSG hello'); self.assertEqual(await read(), 'BEGIN'+(' '+label if label else ''))
            while await read() != 'END':
                pass
        try:
            r,w,send,read = await connect(); await send('NEW'); sid = (await read()).split()[1]
            await reply(send,read,'Claude')
            w.close(); await w.wait_closed()
            for _ in range(30):
                if gateway.sessions[sid].owner is None: break
                await asyncio.sleep(.01)
            r,w,send,read = await connect(); await send('RESUME '+sid)
            self.assertEqual(await read(),'OK RESUME'); await reply(send,read,'Claude')
            for value, expected in [('NVIDIA','NVIDIA'),('unknown',''),('AI','')]:
                provider.label=value; await reply(send,read,expected)
            self.assertEqual(len(gateway.sessions[sid].session.history),10)
            await send('QUIT'); self.assertEqual(await read(),'OK BYE')
            w.close(); await w.wait_closed()
        finally:
            listener.close(); await listener.wait_closed(); await gateway.close()
