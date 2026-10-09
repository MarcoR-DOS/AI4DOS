"""Default DOS config path and English pre-config errors; native client runtime."""
import asyncio
from pathlib import Path
import tempfile
import unittest
from ai4dos.config import Settings
from ai4dos.provider import MockProvider
from ai4dos.server import Gateway

ROOT=Path(__file__).resolve().parents[1]
BINARY=ROOT/'client/build/ai4dos-host'

class RecordingMock(MockProvider):
    def __init__(self):
        super().__init__()
        self.calls = []

    async def stream(self, messages):
        self.calls.append([(m.role, m.text) for m in messages])
        async for delta in super().stream(messages):
            yield delta


class ConfigStartTests(unittest.IsolatedAsyncioTestCase):
    async def run_client(self,folder,*args,input=b'hello\n'):
        proc=await asyncio.create_subprocess_exec(str(BINARY),*args,cwd=folder,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        out,err=await asyncio.wait_for(proc.communicate(input),5)
        return proc.returncode,out,err

    async def test_default_and_explicit_config_en_de(self):
        for language in ('en','de'):
            for explicit in (False,True):
                with self.subTest(language=language,explicit=explicit):
                    secret='s'*32
                    provider=RecordingMock()
                    gateway=Gateway(Settings(port=0,devices={'d':secret}),provider)
                    listener=await gateway.start()
                    try:
                        with tempfile.TemporaryDirectory() as folder:
                            name='CUSTOM.CFG' if explicit else 'AI4DOS.CFG'
                            Path(folder,name).write_text('SERVER=127.0.0.1\nPORT=%s\nDEVICE=d\nSECRET=%s\nLANGUAGE=%s\nCODEPAGE=ASCII\n'%(listener.sockets[0].getsockname()[1],secret,language))
                            code,out,err=await self.run_client(folder,*([name,'hello'] if explicit else []))
                            self.assertEqual(code,0,err)
                            self.assertIn(b'Test reply: hello',out)
                            self.assertEqual(len(provider.calls),1)
                            self.assertEqual([text for _,text in provider.calls[0]],['hello'])
                            self.assertIn(b'System: Verbunden. Du kannst jetzt chatten.' if language=='de' else b'System: Connected. You can start chatting.',out)
                            self.assertIn(b'KI: ' if language=='de' else b'AI: ',out)
                    finally:
                        listener.close();await listener.wait_closed();await gateway.close()

    async def test_missing_invalid_and_unreadable_are_english(self):
        with tempfile.TemporaryDirectory() as folder:
            code,_,err=await self.run_client(folder)
            self.assertNotEqual(code,0);self.assertIn(b'ERROR: AI4DOS.CFG not found.',err)
            Path(folder,'AI4DOS.CFG').write_text('LANGUAGE=de\nPORT=bad\n')
            code,_,err=await self.run_client(folder)
            self.assertNotEqual(code,0);self.assertIn(b'ERROR: AI4DOS.CFG is invalid.',err)
            Path(folder,'AI4DOS.CFG').unlink();Path(folder,'AI4DOS.CFG').mkdir()
            code,_,err=await self.run_client(folder)
            self.assertNotEqual(code,0);self.assertIn(b'could not be read.',err)

    async def test_wrong_device_key_en_de_never_calls_provider(self):
        for language in ('en','de'):
            provider=RecordingMock()
            gateway=Gateway(Settings(port=0,devices={'d':'correct-local-key'}),provider)
            listener=await gateway.start()
            try:
                with tempfile.TemporaryDirectory() as folder:
                    Path(folder,'AI4DOS.CFG').write_text('SERVER=127.0.0.1\nPORT=%s\nDEVICE=d\nSECRET=wrong-local-key\nLANGUAGE=%s\n' % (listener.sockets[0].getsockname()[1],language))
                    code,out,err=await self.run_client(folder,'AI4DOS.CFG','hello',input=None)
                    self.assertNotEqual(code,0)
                    self.assertIn(b'System: Authentifizierung fehlgeschlagen.' if language=='de' else b'System: Authentication failed.',out)
                    self.assertNotIn(b'Gateway unreachable.',out)
                    self.assertEqual(provider.calls,[])
            finally:
                listener.close();await listener.wait_closed();await gateway.close()

    async def test_gateway_unreachable_en_de(self):
        listener=await asyncio.start_server(lambda r,w: w.close(),'127.0.0.1',0)
        port=listener.sockets[0].getsockname()[1]
        listener.close();await listener.wait_closed()
        for language in ('en','de'):
            with tempfile.TemporaryDirectory() as folder:
                Path(folder,'AI4DOS.CFG').write_text('SERVER=127.0.0.1\nPORT=%s\nDEVICE=d\nSECRET=local-test-key\nLANGUAGE=%s\n' % (port,language))
                code,out,err=await self.run_client(folder,'AI4DOS.CFG','hello',input=None)
                self.assertNotEqual(code,0)
                self.assertIn(b'System: Gateway nicht erreichbar.' if language=='de' else b'System: Gateway unreachable.',out)
