"""DOS boundary/Georgi formatter parity; offline local gateway only."""
import asyncio
import ctypes
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import subprocess
import tempfile
import unittest
from ai4dos.config import Settings
from ai4dos.output import render_dos
from ai4dos.protocol import unescape_data
from ai4dos.server import Gateway

ROOT=Path(__file__).resolve().parents[1]
SAMPLE='''# Grüße **DOS**
1. Eins
2. Zwei
* Bullet
> Zitat
```c
x = a * b;
```
| Name | Wert |
| --- | ---: |
| Grüße | ä ö ü Ä Ö Ü ß |
https://example.com/a_b?q=1
[Seite](https://example.com/help)
“Quotes” — ... 😀 🙂 😉 😢 🚀
'''


class EncodingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        output=Path(cls.temp.name)/'charset.dylib'
        subprocess.run(['cc','-std=c89','-Wall','-Wextra','-Werror','-shared','-fPIC','-I'+str(ROOT/'client/include'),str(ROOT/'client/src/charset.c'),'-o',str(output)],check=True)
        cls.lib=ctypes.CDLL(str(output))
        cls.lib.dos_to_utf8.argtypes=[ctypes.c_char_p,ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint]
        cls.lib.dos_to_utf8.restype=ctypes.c_int
        cls.lib.utf8_to_dos.argtypes=cls.lib.dos_to_utf8.argtypes
        cls.lib.utf8_to_dos.restype=ctypes.c_uint

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_complete_codepage_tables_against_standard_codecs(self):
        for cp in (437,850):
            for value in range(128,256):
                source=bytes([value]); expected=source.decode('cp'+str(cp)).encode('utf8')
                target=ctypes.create_string_buffer(20)
                self.assertEqual(self.lib.dos_to_utf8(source,target,20,cp),len(expected))
                self.assertEqual(target.value,expected)
                self.assertEqual(self.lib.utf8_to_dos(expected,target,20,cp),1)
                self.assertEqual(target.value,source)

    def test_ascii_umlauts_limits_and_unicode_fallback(self):
        target=ctypes.create_string_buffer(1001)
        for cp in (437,850):
            text='ASCII ä ö ü Ä Ö Ü ß'
            self.lib.dos_to_utf8(text.encode('cp'+str(cp)),target,1001,cp)
            self.assertEqual(target.value.decode(),text)
            self.lib.utf8_to_dos(text.encode(),target,1001,cp)
            self.assertEqual(target.value,text.encode('cp'+str(cp)))
            self.lib.utf8_to_dos('“a” — • … 🚀'.encode(),target,1001,cp)
            self.assertEqual(target.value,b'"a" - * ... ?')
            self.assertEqual(self.lib.dos_to_utf8(('ä'*501).encode('cp'+str(cp)),target,1001,cp),-1)
            self.assertEqual(target.value,b'')


class RendererTests(unittest.TestCase):
    def test_renderer_baseline(self):
        # Neutral text fixtures keep the regression runnable from a clean checkout.
        fixtures=json.loads((ROOT/'tests/fixtures/dos-render.json').read_text(encoding='utf-8'))
        for case in fixtures:
            options={'width':case['width']} if case['width'] else {}
            self.assertEqual(render_dos(case['input'],**options),case['expected'])

    def test_mixed_markdown_table_code_links_and_emojis(self):
        output=render_dos(SAMPLE)
        self.assertIn('Grüße DOS',output);self.assertIn('1. Eins',output)
        self.assertIn('- Bullet',output);self.assertIn('Zitat',output)
        self.assertIn('  x = a * b;',output);self.assertNotIn('```',output)
        self.assertIn('Name: Grüße',output);self.assertIn('Wert: ä ö ü Ä Ö Ü ß',output)
        self.assertNotIn('| ---',output)
        self.assertIn('https://example.com/a_b?q=1',output)
        self.assertIn('Seite (https://example.com/help)',output)
        self.assertIn(':-D :-) ;-) :-(',output);self.assertNotIn('🚀',output)
        self.assertTrue(all(len(line)<=76 for line in render_dos(SAMPLE,width=76).splitlines()))
        self.assertEqual(render_dos('€ ™ © ®'), 'EUR (TM) (C) (R)')
        self.assertIn('ø',render_dos('CP850 ø'))
        self.assertIn('┌',render_dos('CP437 ┌'))
        self.assertNotIn('\x00',render_dos('a\x00b'))


class GatewayEncodingTests(unittest.IsolatedAsyncioTestCase):
    async def test_dos_bytes_to_utf8_server_and_back_both_codepages(self):
        class Echo:
            def __init__(self):self.seen=[]
            async def stream(self,messages):
                self.seen.append(messages[-1].text)
                yield messages[-1].text
            async def close(self):pass
        for cp in (437,850):
            secret=secrets.token_hex(32);provider=Echo()
            gateway=Gateway(Settings(port=0,devices={'test-device':secret}),provider)
            listener=await gateway.start()
            try:
                with tempfile.TemporaryDirectory() as folder:
                    path=Path(folder)/'client.cfg'
                    path.write_text('SERVER=127.0.0.1\nPORT=%s\nDEVICE=test-device\nSECRET=%s\nCODEPAGE=%s\n'%(listener.sockets[0].getsockname()[1],secret,cp))
                    text='ASCII ä ö ü Ä Ö Ü ß'
                    process=await asyncio.create_subprocess_exec(bytes(str(ROOT/'client/build/ai4dos-host'),'utf8'),bytes(str(path),'utf8'),text.encode('cp'+str(cp)),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
                    stdout,stderr=await asyncio.wait_for(process.communicate(),5)
                    self.assertEqual(process.returncode,0,stderr)
                    self.assertEqual(provider.seen,[text])
                    self.assertIn(text.encode('cp'+str(cp)),stdout)
            finally:
                listener.close();await listener.wait_closed();await gateway.close()

    async def test_shared_dos_render_path_for_all_provider_labels(self):
        for name in ('openai','gemini','nvidia','openrouter','mistral','openai-compatible'):
            class Reply:
                label=name
                async def stream(self,messages):yield SAMPLE
                async def close(self):pass
            secret=secrets.token_hex(32)
            gateway=Gateway(Settings(port=0,devices={'d':secret}),Reply())
            listener=await gateway.start();r,w=await asyncio.open_connection('127.0.0.1',listener.sockets[0].getsockname()[1])
            async def read():return (await asyncio.wait_for(r.readline(),3)).decode().strip('\r\n')
            async def send(text):w.write((text+'\r\n').encode());await w.drain()
            try:
                await read();await send('HELLO d');nonce=(await read()).split()[1]
                await send('AUTH '+hmac.new(secret.encode(),nonce.encode(),hashlib.sha256).hexdigest());await read()
                await send('NEW');await read();await send('MSG test')
                self.assertEqual(await read(),'BEGIN');parts=[]
                while True:
                    line=await read()
                    if line=='END':break
                    self.assertTrue(line.startswith('DATA '),line);parts.append(unescape_data(line[5:]))
                self.assertEqual(''.join(parts),render_dos(SAMPLE))
            finally:
                w.close();await w.wait_closed();listener.close();await listener.wait_closed();await gateway.close()
