import asyncio
import hashlib
import hmac
import secrets
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server/src'))
from ai4dos.config import Settings
from ai4dos.provider import MockProvider
from ai4dos.server import Gateway


class PreAuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.secret = secrets.token_hex(32)
        self.provider = MockProvider()
        self.provider.stream = Mock(side_effect=AssertionError('unexpected provider request'))
        self.gateway = Gateway(Settings(port=0, devices={'dos-pc': self.secret},
                                       max_unauthenticated_connections=1), self.provider)
        self.server = await self.gateway.start()
        self.port = self.server.sockets[0].getsockname()[1]
        self.writers = []

    async def asyncTearDown(self):
        for writer in self.writers:
            writer.close()
            await writer.wait_closed()
        self.server.close()
        await self.server.wait_closed()
        await self.gateway.close()

    async def read(self, reader):
        return (await asyncio.wait_for(reader.readline(), 2)).decode().rstrip('\r\n')

    async def connect(self, accepted=True):
        reader, writer = await asyncio.open_connection('127.0.0.1', self.port)
        self.writers.append(writer)
        self.assertEqual(await self.read(reader), 'OK AI4DOS/0.3 UTF-8' if accepted
                         else 'ERROR LIMIT connection limit')
        return reader, writer

    async def send(self, writer, line):
        writer.write((line + '\r\n').encode())
        await writer.drain()

    async def auth(self, reader, writer):
        await self.send(writer, 'HELLO dos-pc')
        challenge = (await self.read(reader)).split()[1]
        digest = hmac.new(self.secret.encode(), challenge.encode(), hashlib.sha256).hexdigest()
        await self.send(writer, 'AUTH ' + digest)
        self.assertEqual(await self.read(reader), 'OK AUTH')
        return challenge, digest

    async def wait_slots(self, expected):
        async def wait():
            while self.gateway.preauth_connections != expected:
                await asyncio.sleep(.005)
        await asyncio.wait_for(wait(), 1)

    async def test_absolute_deadline_despite_regular_commands(self):
        self.gateway.settings.auth_timeout = .15
        reader, writer = await self.connect()
        errors = []
        for i in range(30):
            await self.send(writer, 'NEW' if i % 2 else 'invalid')
            response = await self.read(reader)
            errors.append(response)
            if response == 'ERROR AUTH_REQUIRED authentication timeout':
                break
            await asyncio.sleep(.01)
        self.assertIn('ERROR AUTH_REQUIRED authentication timeout', errors)
        self.assertGreater(len(errors), 2)
        self.assertEqual(await self.read(reader), '')
        await self.wait_slots(0)
        self.assertFalse(self.gateway.sessions)
        self.provider.stream.assert_not_called()

    async def test_auth_releases_slot_and_disables_deadline(self):
        self.gateway.settings.auth_timeout = .15
        reader, writer = await self.connect()
        await self.auth(reader, writer)
        await self.wait_slots(0)
        second, second_writer = await self.connect()
        self.assertEqual(self.gateway.preauth_connections, 1)
        await asyncio.sleep(.2)
        await self.send(writer, 'NEW')
        self.assertTrue((await self.read(reader)).startswith('SESSION '))
        await self.send(writer, 'QUIT')
        self.assertEqual(await self.read(reader), 'OK BYE')
        self.assertEqual(await self.read(reader), '')
        self.assertEqual(await self.read(second), 'ERROR AUTH_REQUIRED authentication timeout')
        self.assertEqual(await self.read(second), '')
        await self.wait_slots(0)

    async def test_limit_and_disconnect_release(self):
        reader, writer = await self.connect()
        rejected, _ = await self.connect(accepted=False)
        self.assertEqual(await self.read(rejected), '')
        self.assertEqual(self.gateway.preauth_connections, 1)
        writer.close()
        await writer.wait_closed()
        await self.wait_slots(0)
        await self.connect()

    async def test_timeout_releases_slot(self):
        self.gateway.settings.auth_timeout = .05
        reader, _ = await self.connect()
        self.assertEqual(await self.read(reader), 'ERROR AUTH_REQUIRED authentication timeout')
        self.assertEqual(await self.read(reader), '')
        await self.wait_slots(0)
        await self.connect()

    async def test_oversized_line_releases_slot(self):
        reader, writer = await self.connect()
        await self.send(writer, 'x' * 2000)
        self.assertEqual(await self.read(reader), 'ERROR LINE_TOO_LONG command exceeds limit')
        self.assertEqual(await self.read(reader), '')
        await self.wait_slots(0)
        await self.connect()

    async def test_auth_failure_log_exact_and_secret_free(self):
        for device in ('dos-pc', 'unknown-device'):
            reader, writer = await self.connect()
            await self.send(writer, 'HELLO ' + device)
            challenge = (await self.read(reader)).split()[1]
            digest = '0' * 64
            with self.assertLogs('ai4dos', level='WARNING') as logs:
                await self.send(writer, 'AUTH ' + digest)
                self.assertEqual(await self.read(reader), 'ERROR AUTH_FAILED device authentication failed')
                self.assertEqual(await self.read(reader), '')
            self.assertEqual(len(logs.records), 1)
            record = logs.records[0]
            self.assertEqual(record.getMessage(), 'AUTH_FAILED peer=127.0.0.1 device=' + device)
            self.assertIsNone(record.exc_info)
            for sensitive in (self.secret, digest, challenge):
                self.assertNotIn(sensitive, '\n'.join(logs.output))
            await self.wait_slots(0)
        self.assertFalse(self.gateway.sessions)
        self.provider.stream.assert_not_called()

    async def test_handler_error_and_cancellation_release(self):
        for exc in (ConnectionError(), RuntimeError('synthetic error'), asyncio.CancelledError()):
            reader = Mock(readline=AsyncMock(side_effect=exc))
            writer = Mock(drain=AsyncMock(), wait_closed=AsyncMock())
            if isinstance(exc, ConnectionError):
                await self.gateway.handle(reader, writer)
            else:
                with self.assertRaises(type(exc)):
                    await self.gateway.handle(reader, writer)
            self.assertEqual(self.gateway.preauth_connections, 0)
            self.assertFalse(self.gateway.tasks)
            writer.close.assert_called_once()

    async def test_deadline_includes_blocked_greeting_write(self):
        self.gateway.settings.auth_timeout = .03
        stalled = asyncio.Event()
        reader = Mock(readline=AsyncMock())
        writer = Mock(drain=AsyncMock(side_effect=stalled.wait), wait_closed=AsyncMock())
        await asyncio.wait_for(self.gateway.handle(reader, writer), 1.5)
        self.assertEqual(self.gateway.preauth_connections, 0)
        reader.readline.assert_not_called()
        writer.close.assert_called_once()


class PreAuthConfigTests(unittest.TestCase):
    def test_defaults_and_validation(self):
        settings = Settings(devices={'d': '12345678'})
        self.assertEqual(settings.auth_timeout, 30)
        self.assertEqual(settings.max_unauthenticated_connections, 16)
        for field, values in [('auth_timeout', [0, -1, float('inf'), float('nan'), True, '30']),
                              ('max_unauthenticated_connections', [0, -1, 1.5, True, '16'])]:
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    Settings(devices={'d': '12345678'}, **{field: value})


if __name__ == '__main__':
    unittest.main()
