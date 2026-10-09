"""Manual device pairing contracts; mock provider and loopback only."""
import asyncio
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

from ai4dos.config import Settings, ConfigurationError
from ai4dos.provider import MockProvider
from ai4dos.server import Gateway, run

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / 'client/build/ai4dos-host'


class DeviceKeyTests(unittest.TestCase):
    def test_manual_keys_and_custom_devices_are_read_without_changes(self):
        for key in ('Abcd1234', 'Letters123456', 'Letters1234567890', 'x' * 64,
                    'z' * 128, 'Abcd!234'):
            with self.subTest(length=len(key)), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'gateway.json'
                devices = {'dos-pc': key, 'custom': 'Custom123'}
                original = {'devices': devices, 'provider': 'mock', 'instructions': 'Änderung'}
                path.write_text(json.dumps(original))
                path.chmod(0o444)
                before = path.read_bytes()
                self.assertEqual(Settings.load(path).devices, devices)
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(list(Path(folder).iterdir()), [path])
        self.assertEqual(Settings(devices={'custom': 'Custom123'}).devices,
                         {'custom': 'Custom123'})

    def test_invalid_devices_have_clear_errors_and_are_not_repaired(self):
        invalid = ({}, {'devices': {}}, {'devices': None}, {'devices': []},
                   {'devices': {'dos-pc': 'short'}},
                   {'devices': {'dos-pc': '1234567'}},
                   {'devices': {'dos-pc': 'x' * 129}},
                   {'devices': {'dos-pc': 'Abcd 1234'}},
                   {'devices': {'dos-pc': 'Abcd\t1234'}},
                   {'devices': {'dos-pc': 'Abcdä1234'}},
                   {'devices': {'dos-pc': 12345678}},
                   {'devices': {'bad id': 'Abcd1234'}},
                   {'devices': {'custom': 'Custom123', 'bad': 'short'}})
        for values in invalid:
            with self.subTest(values=values), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'gateway.json'
                path.write_text(json.dumps(values))
                before = path.read_bytes()
                with self.assertRaisesRegex(ConfigurationError, '[Dd]evice'):
                    Settings.load(path)
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_cli_reports_invalid_device_config_without_key_leaks(self):
        for values, message in (({}, 'Device configuration missing or empty'),
                                ({'devices': {}}, 'Device configuration missing or empty'),
                                ({'devices': {'dos-pc': 'short'}}, 'Device key must be 8-128')):
            with self.subTest(values=values), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'gateway.json'
                path.write_text(json.dumps(values))
                env = dict(os.environ, PYTHONPATH=str(ROOT / 'server/src'))
                result = subprocess.run([sys.executable, '-m', 'ai4dos.server', '--config', str(path)],
                                        env=env, capture_output=True, text=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertNotIn('short', result.stdout + result.stderr)
                self.assertEqual(json.loads(path.read_text()), values)

    def test_compose_mounts_are_read_only_without_uid_overrides(self):
        compose = (ROOT / 'docker-compose.yml').read_text()
        mounts = compose.split('    volumes:\n')[1].split('\n    read_only: true\n')[0]
        gateway, provider = mounts.split('      - type: bind')[1:]
        self.assertIn('source: ./config.local/gateway.json\n', gateway)
        self.assertIn('target: /config/gateway.json\n', gateway)
        self.assertIn('read_only: true', gateway)
        self.assertIn('source: ./config.local/provider.cfg', provider)
        self.assertIn('read_only: true', provider)
        self.assertIn('user: "10001:10001"', compose)
        self.assertNotIn('AI4DOS_UID', compose)
        self.assertNotIn('AI4DOS_GID', compose)

    def test_native_client_rejects_invalid_keys(self):
        for key in ('1234567', 'Abcd 1234', 'Abcd\t1234', 'x' * 129):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'AI4DOS.CFG'
                path.write_text('SERVER=127.0.0.1\nPORT=1983\nDEVICE=dos-pc\nSECRET=' + key + '\n')
                result = subprocess.run([str(BINARY), str(path), 'hello'], capture_output=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'is invalid.', result.stderr)


class GatewayDeviceStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_config_remains_clear_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'missing.json'
            with self.assertRaisesRegex(ConfigurationError, 'Gateway config is missing'):
                await run(path)
            self.assertFalse(path.exists())

    async def test_same_manual_key_authenticates_native_dos_code_and_gateway(self):
        for key in ('Abcd1234', 'Letters123456', 'Letters1234567890', 'x' * 128):
            with self.subTest(length=len(key)), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'gateway.json'
                path.write_text(json.dumps({'devices': {'dos-pc': key}, 'provider': 'mock', 'port': 0}))
                gateway = Gateway(Settings.load(path), MockProvider())
                listener = await gateway.start()
                try:
                    cfg = Path(folder) / 'AI4DOS.CFG'
                    cfg.write_text('SERVER=127.0.0.1\nPORT=%s\nDEVICE=dos-pc\nSECRET=%s\n' %
                                   (listener.sockets[0].getsockname()[1], key))
                    process = await asyncio.create_subprocess_exec(str(BINARY), str(cfg), 'hello',
                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    out, err = await asyncio.wait_for(process.communicate(), 5)
                    self.assertEqual(process.returncode, 0, err)
                    self.assertIn(b'Test reply: hello', out)
                finally:
                    listener.close()
                    await listener.wait_closed()
                    await gateway.close()

    async def test_actual_gateway_restarts_never_write_config_or_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'gateway.json'
            path.write_text('{"devices":{"custom":"Custom123"},"provider":"mock","port":0}')
            path.chmod(0o444)
            before = path.read_bytes()
            env = dict(os.environ, PYTHONPATH=str(ROOT / 'server/src'))
            for _ in range(2):
                process = await asyncio.create_subprocess_exec(sys.executable, '-m', 'ai4dos.server',
                    '--config', str(path), env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                try:
                    line = await asyncio.wait_for(process.stdout.readline(), 10)
                    self.assertIn(b'AI4DOS gateway ready', line)
                    self.assertEqual(path.read_bytes(), before)
                    self.assertEqual(list(Path(folder).iterdir()), [path])
                    process.send_signal(signal.SIGINT)
                    out, err = await asyncio.wait_for(process.communicate(), 10)
                    self.assertEqual(process.returncode, 0, err)
                    self.assertNotIn(b'Custom123', line + out + err)
                finally:
                    if process.returncode is None:
                        process.kill()
                        await process.wait()
