import asyncio
import hashlib
import hmac
import secrets
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server/src'))
from ai4dos.config import Settings
from ai4dos.server import Gateway
from ai4dos.provider import MockProvider
from ai4dos.protocol import GREETING, ProtocolError, parse_command, data_frames, unescape_data
from ai4dos.output import render_dos
from ai4dos.session import Role, Message, Session
from ai4dos.openai_provider import OpenAIProvider, ExactTokenFilter


class CoreTests(unittest.TestCase):
    def test_parser(self):
        self.assertEqual(parse_command('HELLO test-device'), ('HELLO', 'test-device'))
        for text in ['MODE PUBLIC', 'AUTH USER token', 'NEW extra', 'MSG ', 'MSG a\rb', 'HELLO bad id', 'MSG ' + 'x'*1001]:
            with self.assertRaises(ProtocolError):
                parse_command(text)

    def test_frame_round_trip(self):
        text = ('Ä\n\r\t\\€z' * 300)
        frames = list(data_frames(text))
        self.assertGreater(len(frames), 1)
        self.assertTrue(all(len(f[5:].encode()) <= 512 for f in frames))
        self.assertEqual(''.join(unescape_data(f[5:]) for f in frames), text)
        with self.assertRaises(ProtocolError):
            unescape_data('bad\\q')

    def test_dos_output(self):
        output = render_dos('\x1b[31m# Grüße “test” €\r\n\x00a\x1b[0m')
        self.assertEqual(output, 'Grüße "test" EUR\na')
        self.assertEqual(output.encode("cp437").decode("cp437"), output)

    def test_session_roles_and_history(self):
        session = Session(max_exchanges=1)
        self.assertRegex(session.session_id, '^[0-9a-f]{12}$')
        session.record('first', 'reply1')
        session.record('second', 'reply2')
        self.assertEqual(session.history, [Message(Role.ROLE_USER, 'second'), Message(Role.ROLE_AI, 'reply2')])
        self.assertEqual({r.name for r in Role}, {'ROLE_USER', 'ROLE_AI', 'ROLE_SYSTEM'})

    def test_filter(self):
        f = ExactTokenFilter()
        output = ''.join(f.feed(s) for s in ['abc<|fi', 'm_suf', 'fix|> plain fim_suffix ‹¡fim_', 'suffix!> <|fi']) + f.finish()
        self.assertEqual(output, 'abc plain fim_suffix  <|fi')

    def test_config_rejects_bad_secret_and_output(self):
        with self.assertRaises(ValueError):
            Settings(devices={'d': 'short'})
        with self.assertRaises(ValueError):
            Settings(devices={'d': secrets.token_hex(32)}, output_mode='auto')


class FakeStream:
    def __init__(self, events):
        self.events, self.closed = events, False
    def __aiter__(self):
        return self.iterate()
    async def iterate(self):
        for event in self.events:
            yield SimpleNamespace(**event)
    async def close(self):
        self.closed = True


class FakeSDK:
    def __init__(self, events):
        self.responses = self
        self.stream = FakeStream(events)
        self.closed = False
    async def create(self, **kwargs):
        self.request = kwargs
        return self.stream
    async def close(self):
        self.closed = True


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_openai_mapping_stream_close(self):
        client = FakeSDK([{'type': 'response.output_text.delta', 'delta': 'ok<|fim_suffix|>'}, {'type': 'response.completed'}])
        provider = OpenAIProvider(client=client, model='test-model', instructions='neutral')
        reply = ''.join([x async for x in provider.stream([Message(Role.ROLE_USER, 'hello'), Message(Role.ROLE_AI, 'answer'), Message(Role.ROLE_SYSTEM, 'note')])])
        self.assertEqual(reply, 'ok')
        self.assertEqual([m['role'] for m in client.request['input']], ['user', 'assistant', 'system'])
        self.assertFalse(client.request['store'])
        self.assertTrue(client.stream.closed)
        await provider.close()
        self.assertTrue(client.closed)

    async def test_openai_failure_incomplete_and_missing_terminal(self):
        for event in ['response.failed', 'response.incomplete', 'error', 'response.created']:
            client = FakeSDK([{'type': event}])
            provider = OpenAIProvider(client=client, model='test-model', instructions='neutral')
            with self.assertRaises(RuntimeError):
                [x async for x in provider.stream([])]
            self.assertTrue(client.stream.closed)


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.secret = secrets.token_hex(32)
        self.gateway = Gateway(Settings(port=0, devices={'test-device': self.secret}), MockProvider())
        self.server = await self.gateway.start()
        self.port = self.server.sockets[0].getsockname()[1]
        self.connections = []

    async def asyncTearDown(self):
        for writer in self.connections:
            writer.close()
            await writer.wait_closed()
        self.server.close()
        await self.server.wait_closed()
        await self.gateway.close()

    async def connect(self):
        reader, writer = await asyncio.open_connection('127.0.0.1', self.port)
        self.connections.append(writer)
        self.assertEqual(await self.read(reader), GREETING)
        return reader, writer

    async def read(self, reader):
        return (await asyncio.wait_for(reader.readline(), 3)).decode().strip('\r\n')

    async def send(self, writer, text):
        writer.write((text+'\r\n').encode())
        await writer.drain()

    async def authenticate(self, reader, writer, secret=None, device='test-device'):
        await self.send(writer, 'HELLO ' + device)
        nonce = (await self.read(reader)).split()[1]
        digest = hmac.new((secret or self.secret).encode(), nonce.encode(), hashlib.sha256).hexdigest()
        await self.send(writer, 'AUTH ' + digest)
        return await self.read(reader), digest

    async def test_e2e_session_history_new_close(self):
        r,w = await self.connect()
        self.assertEqual((await self.authenticate(r,w))[0], 'OK AUTH')
        await self.send(w, 'NEW')
        session1 = await self.read(r)
        self.assertRegex(session1, '^SESSION [0-9a-f]{12}$')
        await self.send(w, 'MSG hello')
        self.assertEqual(await self.read(r), 'BEGIN')
        reply = []
        while True:
            line = await self.read(r)
            if line == 'END': break
            self.assertTrue(line.startswith('DATA '))
            reply.append(unescape_data(line[5:]))
        self.assertEqual(''.join(reply), 'Test reply: hello')
        await self.send(w, 'NEW')
        self.assertNotEqual(await self.read(r), session1)
        await self.send(w, 'QUIT')
        self.assertEqual(await self.read(r), 'OK BYE')
        self.assertEqual(await self.read(r), '')

    async def test_auth_and_replay_state(self):
        r,w = await self.connect()
        await self.send(w,'MSG before-auth')
        self.assertTrue((await self.read(r)).startswith('ERROR AUTH_REQUIRED'))
        result,digest = await self.authenticate(r,w)
        self.assertEqual(result, 'OK AUTH')
        await self.send(w,'AUTH ' + digest)
        self.assertTrue((await self.read(r)).startswith('ERROR BAD_STATE'))
        await self.send(w,'MSG before-new')
        self.assertTrue((await self.read(r)).startswith('ERROR BAD_STATE'))

    async def test_bad_and_unknown_devices_same_failure(self):
        for secret, device in [(secrets.token_hex(32),'test-device'),(self.secret,'unknown')]:
            r,w = await self.connect()
            result,_ = await self.authenticate(r,w,secret,device)
            self.assertEqual(result,'ERROR AUTH_FAILED device authentication failed')
            self.assertEqual(await self.read(r),'')

    async def test_provider_error_no_end_and_recover(self):
        class Broken(MockProvider):
            async def stream(self, messages):
                yield 'partial'
                raise RuntimeError('private upstream detail must not reach wire')
        self.gateway.provider = Broken()
        r,w = await self.connect()
        await self.authenticate(r,w)
        await self.send(w,'NEW'); await self.read(r)
        await self.send(w,'MSG error')
        self.assertEqual(await self.read(r),'BEGIN')
        self.assertEqual(await self.read(r),'ERROR UPSTREAM response generation failed')
        await self.send(w,'QUIT')
        self.assertEqual(await self.read(r),'OK BYE')

    async def test_connection_limit_cleanup(self):
        a,b = await self.connect(),await self.connect()
        await self.authenticate(*a);await self.authenticate(*b)
        r,w=await self.connect()
        self.assertTrue((await self.authenticate(r,w))[0].startswith('ERROR LIMIT'))
        await self.send(a[1],'QUIT');await self.read(a[0]);await self.read(a[0])
        r,w=await self.connect()
        self.assertEqual((await self.authenticate(r,w))[0],'OK AUTH')

    async def test_message_utf8_byte_boundaries_and_truncated_sequence(self):
        r,w = await self.connect()
        await self.authenticate(r,w)
        await self.new_session(r,w)
        for text in ('x'*999, 'x'*1000, 'x'*997 + 'ä', 'x'*998 + 'ä', 'x'*996 + '😀'):
            self.assertIn('Test reply:', await self.exchange(r,w,text))
        for text in ('x'*1001, 'x'*999 + 'ä', 'x'*997 + '😀'):
            await self.send(w,'MSG ' + text)
            self.assertTrue((await self.read(r)).startswith('ERROR TOO_LONG'))
        w.write(b'MSG ' + b'x'*998 + b'\xc3\r\n')
        await w.drain()
        self.assertTrue((await self.read(r)).startswith('ERROR BAD_ENCODING'))
        # Rejected frames leave the connection and gateway usable.
        self.assertIn('recovered', await self.exchange(r,w,'recovered'))

    async def test_line_limit_encoding_private_commands(self):
        r,w=await self.connect()
        w.write(b'HELLO \xff\r\n');await w.drain()
        self.assertTrue((await self.read(r)).startswith('ERROR BAD_ENCODING'))
        await self.send(w,'MODE PUBLIC')
        self.assertTrue((await self.read(r)).startswith('ERROR BAD_COMMAND'))
        await self.send(w,'x'*2000)
        self.assertTrue((await self.read(r)).startswith('ERROR LINE_TOO_LONG'))
        self.assertEqual(await self.read(r),'')

    async def test_dos_collects_before_data_utf8_progressive(self):
        reached = asyncio.Event()
        release = asyncio.Event()
        class Delayed(MockProvider):
            async def stream(self,messages):
                yield 'one'
                reached.set()
                await release.wait()
                yield 'two'
        self.gateway.provider=Delayed()
        r,w=await self.connect(); await self.authenticate(r,w)
        await self.send(w,'NEW');await self.read(r)
        await self.send(w,'MSG hi'); self.assertEqual(await self.read(r),'BEGIN')
        await asyncio.wait_for(reached.wait(),3)
        pending = asyncio.create_task(r.readline())
        await asyncio.sleep(0.03)
        self.assertFalse(pending.done())
        release.set()
        self.assertEqual((await pending).decode().strip(),'DATA onetwo')
        self.assertEqual(await self.read(r),'END')
        self.gateway.settings.output_mode='utf8'
        release.clear();reached.clear()
        await self.send(w,'MSG hi');self.assertEqual(await self.read(r),'BEGIN')
        self.assertEqual(await self.read(r),'DATA one')
        release.set();self.assertEqual(await self.read(r),'DATA two');self.assertEqual(await self.read(r),'END')

    async def new_session(self, r, w):
        await self.send(w, 'NEW')
        return (await self.read(r)).split()[1]

    async def disconnect(self, r, w):
        w.close()
        await w.wait_closed()
        for _ in range(100):
            if not self.gateway.active:
                return
            await asyncio.sleep(.01)
        self.fail('connection lease not released')

    async def exchange(self, r, w, text):
        await self.send(w, 'MSG ' + text)
        self.assertEqual(await self.read(r), 'BEGIN')
        frames = []
        while True:
            line = await self.read(r)
            if line == 'END':
                return ''.join(unescape_data(x[5:]) for x in frames)
            self.assertTrue(line.startswith('DATA '), line)
            frames.append(line)

    async def test_resume_cycles_auth_history_and_newest_session(self):
        r,w = await self.connect(); await self.authenticate(r,w)
        sid = await self.new_session(r,w)
        for i in range(8):
            await self.exchange(r,w,'message-' + str(i))
            await self.disconnect(r,w)
            r,w = await self.connect()
            await self.send(w,'RESUME ' + sid)
            self.assertTrue((await self.read(r)).startswith('ERROR AUTH_REQUIRED'))
            self.assertEqual((await self.authenticate(r,w))[0], 'OK AUTH')
            await self.send(w,'RESUME ' + sid)
            self.assertEqual(await self.read(r),'OK RESUME')
            self.assertEqual(len(self.gateway.sessions[sid].session.history),2*(i+1))
        newest = await self.new_session(r,w)
        self.assertNotEqual(sid,newest)
        await self.disconnect(r,w)
        r,w = await self.connect(); await self.authenticate(r,w)
        await self.send(w,'RESUME ' + newest)
        self.assertEqual(await self.read(r),'OK RESUME')
        self.assertEqual(self.gateway.sessions[newest].session.history,[])
        await self.exchange(r,w,'newest')
        self.assertEqual(len(self.gateway.sessions[newest].session.history),2)
        self.assertEqual(len(self.gateway.sessions[sid].session.history),16)

    async def test_resume_unknown_foreign_busy_and_restart(self):
        self.gateway.settings.devices['other'] = secrets.token_hex(32)
        r,w = await self.connect(); await self.authenticate(r,w)
        sid = await self.new_session(r,w)
        r2,w2 = await self.connect(); await self.authenticate(r2,w2)
        await self.send(w2,'RESUME ' + sid)
        self.assertTrue((await self.read(r2)).startswith('ERROR SESSION_BUSY'))
        await self.send(w2,'QUIT'); await self.read(r2); await self.read(r2)
        r2,w2 = await self.connect()
        await self.authenticate(r2,w2,self.gateway.settings.devices['other'],'other')
        for target in (sid,'ffffffffffff'):
            await self.send(w2,'RESUME ' + target)
            self.assertEqual(await self.read(r2),'ERROR SESSION session unavailable')
        self.gateway.sessions.clear()  # Lost in-memory registry, as after restart.
        await self.send(w,'RESUME ' + sid)
        self.assertEqual(await self.read(r),'ERROR SESSION session unavailable')
        new = await self.new_session(r,w)
        self.assertNotEqual(sid,new)

    async def test_real_gateway_restart_loses_registry(self):
        r,w = await self.connect(); await self.authenticate(r,w)
        sid = await self.new_session(r,w)
        await self.disconnect(r,w)
        self.server.close(); await self.server.wait_closed(); await self.gateway.close()
        self.gateway = Gateway(Settings(port=0,devices={'test-device':self.secret}),MockProvider())
        self.server = await self.gateway.start(); self.port = self.server.sockets[0].getsockname()[1]
        r,w = await self.connect(); await self.authenticate(r,w)
        await self.send(w,'RESUME ' + sid)
        self.assertEqual(await self.read(r),'ERROR SESSION session unavailable')
        self.assertNotEqual(await self.new_session(r,w),sid)

    async def test_resume_expiration_and_bounded_registry(self):
        self.gateway.settings.max_sessions_per_device = 2
        self.gateway.settings.session_ttl = .03
        r,w = await self.connect(); await self.authenticate(r,w)
        ids = [await self.new_session(r,w) for _ in range(4)]
        self.assertEqual(len(self.gateway.sessions),2)
        self.assertNotIn(ids[0],self.gateway.sessions)
        await self.disconnect(r,w); await asyncio.sleep(.05)
        r,w = await self.connect(); await self.authenticate(r,w)
        await self.send(w,'RESUME ' + ids[-1])
        self.assertEqual(await self.read(r),'ERROR SESSION session unavailable')
        self.assertFalse(self.gateway.sessions)

    async def test_interrupted_reply_has_no_replay_and_accepts_new_message(self):
        class Interrupted(Gateway):
            async def respond(gateway, writer, session, message):
                if message == 'interrupt':
                    await gateway.write(writer,'BEGIN')
                    await gateway.write(writer,'DATA accepted-partial')
                    writer.close()
                    return
                await super(Interrupted,gateway).respond(writer,session,message)
        self.server.close(); await self.server.wait_closed(); await self.gateway.close()
        self.gateway = Interrupted(Settings(port=0,devices={'test-device':self.secret}),MockProvider())
        self.server = await self.gateway.start(); self.port = self.server.sockets[0].getsockname()[1]
        r,w = await self.connect(); await self.authenticate(r,w)
        sid = await self.new_session(r,w)
        await self.send(w,'MSG interrupt')
        self.assertEqual(await self.read(r),'BEGIN')
        self.assertEqual(await self.read(r),'DATA accepted-partial')
        self.assertEqual(await self.read(r),'')
        await self.disconnect(r,w)
        r,w = await self.connect(); await self.authenticate(r,w)
        await self.send(w,'RESUME ' + sid)
        self.assertEqual(await self.read(r),'OK RESUME')
        self.assertEqual(self.gateway.sessions[sid].session.history,[])
        self.assertIn('next',await self.exchange(r,w,'next'))

    async def test_native_client_same_main_auth_reply_close(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'client/build') as folder:
            cfg = Path(folder)/'CLIENT.CFG'
            cfg.write_text(f'SERVER=127.0.0.1\nPORT={self.port}\nDEVICE=test-device\nSECRET={self.secret}\n')
            cfg.chmod(0o600)
            proc = await asyncio.create_subprocess_exec(str(ROOT/'client/build/ai4dos-host'), str(cfg), 'hello native',stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            stdout,stderr = await asyncio.wait_for(proc.communicate(),5)
            self.assertEqual(proc.returncode,0,stderr.decode())
            self.assertEqual(stdout.decode(),'System: Connecting to gateway...\nSystem: Connected. You can start chatting.\nAI: Test reply: hello native\n')

    async def test_native_client_auth_error(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'client/build') as folder:
            cfg=Path(folder)/'CLIENT.CFG'
            cfg.write_text(f'SERVER=127.0.0.1\nPORT={self.port}\nDEVICE=test-device\nSECRET={secrets.token_hex(32)}\n')
            proc=await asyncio.create_subprocess_exec(str(ROOT/'client/build/ai4dos-host'),str(cfg),'hello',stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            _,err=await asyncio.wait_for(proc.communicate(),5)
            self.assertNotEqual(proc.returncode,0)
            self.assertIn('AUTH_FAILED',err.decode())

    async def test_native_client_outputs_data_before_end(self):
        release = asyncio.Event()
        class Delayed(MockProvider):
            async def stream(self, messages):
                yield 'first'
                await release.wait()
                yield 'second'
        self.gateway.provider = Delayed()
        self.gateway.settings.output_mode = 'utf8'
        with tempfile.TemporaryDirectory(dir=ROOT/'client/build') as folder:
            cfg = Path(folder)/'CLIENT.CFG'
            cfg.write_text(f'SERVER=127.0.0.1\nPORT={self.port}\nDEVICE=test-device\nSECRET={self.secret}\n')
            cfg.chmod(0o600)
            proc = await asyncio.create_subprocess_exec(str(ROOT/'client/build/ai4dos-host'), str(cfg), 'hello', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                self.assertEqual(await asyncio.wait_for(proc.stdout.readline(),3),b'System: Connecting to gateway...\n')
                self.assertEqual(await asyncio.wait_for(proc.stdout.readline(),3),b'System: Connected. You can start chatting.\n')
                first = await asyncio.wait_for(proc.stdout.readexactly(len(b'AI: first')), 3)
                self.assertEqual(first, b'AI: first')
                self.assertIsNone(proc.returncode)
                release.set()
                stdout, stderr = await asyncio.wait_for(proc.communicate(), 5)
                self.assertEqual(proc.returncode, 0, stderr.decode())
                self.assertEqual(stdout, b'second\n')
            finally:
                release.set()
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()


if __name__ == '__main__':
    unittest.main()
