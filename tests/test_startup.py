"""Offline startup contracts: synthetic keys only, no provider requests."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, AsyncMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server/src'))
from ai4dos.config import Settings, build_provider, ConfigurationError
from ai4dos import server

KEY = 'SYNTHETIC_TEST_KEY_DO_NOT_USE'
DEVICE = 'a' * 64


class StartupTests(unittest.TestCase):
    def cli(self, values=None, provider_text=None, script=False):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'gateway.local.json'
            if values is not None:
                if provider_text is not None:
                    cfg = Path(folder) / 'provider.local.cfg'
                    cfg.write_text(provider_text)
                    values = dict(values, provider_config=cfg.name)
                path.write_text(json.dumps(values))
            command = [str(ROOT / 'start.sh')] if script else [sys.executable, '-m', 'ai4dos.server']
            env = dict(os.environ, PYTHONPATH=str(ROOT / 'server/src'))
            for name in list(env):
                if name.endswith('API_KEY'):
                    del env[name]
            result = subprocess.run(command + ['--config', str(path)], cwd=folder,
                                    env=env, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            text = result.stdout + result.stderr
            self.assertNotIn('Traceback', text)
            self.assertNotIn(KEY, text)
            return text

    def test_default_and_missing_config(self):
        example = (ROOT / 'server/provider.example.cfg').read_text()
        self.assertIn('PROVIDER=openrouter', example)
        self.assertIn('MODEL=openrouter/free', example)
        self.assertIn('API_KEY=\n', example)
        self.assertIn('REASONING=none', example)
        self.assertIn('Gateway config is missing', self.cli())
        sample = json.loads((ROOT / 'server/gateway.example.json').read_text())
        self.assertEqual(sample['devices'], {'dos-pc': '<KEY>'})
        with self.assertRaises(ValueError):
            Settings(devices=sample['devices'])  # The user must replace the short placeholder.

    def test_missing_key_unknown_provider_and_model(self):
        base = {'devices': {'dos-pc': DEVICE}, 'provider': 'openrouter'}
        self.assertIn('No API key configured', self.cli(base))
        self.assertIn('Unknown provider', self.cli(dict(base, provider=KEY)))
        self.assertIn('Model is missing', self.cli(dict(base, provider='openai')))
        for model in [' ', 'bad model', '\n' + KEY, 42]:
            self.assertIn('Model is invalid', self.cli(dict(base, model=model)))
        self.assertIn('Provider configuration invalid', self.cli(dict(base, api_key=KEY, port='bad')))
        self.assertIn('Configuration file is missing', self.cli(dict(base, api_key_file='missing.local')))

    def test_example_routes_to_openrouter_missing_key(self):
        self.assertIn('No API key configured', self.cli(
            {'devices': {'dos-pc': DEVICE}},
            (ROOT / 'server/provider.example.cfg').read_text()))

    def test_mac_linux_starter_from_other_directory(self):
        self.assertIn('No API key configured', self.cli(
            {'devices': {'dos-pc': DEVICE}, 'provider': 'openrouter'}, script=True))

    def test_windows_starter_contract(self):
        script = (ROOT / 'START.BAT').read_bytes()
        self.assertIn(b'\r\n', script)
        for required in (b'cd /d "%~dp0"', b'if not exist', b'set "PYTHONPATH=%CD%\\server\\src"',
                         b'".venv\\Scripts\\python.exe" -m ai4dos.server %*', b'exit /b %ERRORLEVEL%'):
            self.assertIn(required, script)


class ProviderStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_six_provider_configs_and_key_sources(self):
        models = {'openrouter': 'openrouter/free', 'openai': 'gpt-6-luna',
                  'gemini': 'gemini-2.5-flash', 'nvidia': 'nvidia/nemotron-3-super-120b-a12b',
                  'mistral': 'mistral-small-latest', 'openai-compatible': 'local-model'}
        for name, model in models.items():
            for source in ('config', 'environment', 'file'):
                with self.subTest(provider=name, source=source), tempfile.TemporaryDirectory() as folder:
                    folder = Path(folder)
                    cfg = folder / 'provider.local.cfg'
                    text = 'PROVIDER=%s\nMODEL=%s\nREASONING=none\n' % (name, model)
                    if name == 'openai-compatible':
                        text += 'BASE_URL=https://example.invalid/v1\n'
                    if source == 'file':
                        (folder / 'key.local').write_text(KEY)
                        text += 'API_KEY_FILE=key.local\n'
                    elif source == 'config':
                        text += 'API_KEY=' + KEY + '\n'
                    cfg.write_text(text)
                    path = folder / 'gateway.local.json'
                    path.write_text(json.dumps({'devices': {'dos-pc': DEVICE}, 'provider_config': cfg.name}))
                    with patch.dict(os.environ, {'API_KEY': KEY} if source == 'environment' else {}, clear=True):
                        settings = Settings.load(path)
                        self.assertEqual(settings.reasoning, 'none')
                        self.assertNotIn(KEY, repr(settings))
                        provider = build_provider(settings)
                        await provider.close()

    async def test_occupied_port_cli_and_secret_safe_parse_errors(self):
        listener = await asyncio.start_server(lambda r,w: w.close(), '127.0.0.1', 0)
        try:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'gateway.local.json'
                path.write_text(json.dumps({'devices': {'dos-pc': DEVICE}, 'provider': 'mock',
                                           'port': listener.sockets[0].getsockname()[1]}))
                for content, expected in ((path.read_text(), 'Cannot listen on port'),
                                          ('{"api_key":"' + KEY + '",', 'Provider configuration invalid')):
                    path.write_text(content)
                    proc = await asyncio.create_subprocess_exec(str(ROOT / 'start.sh'), '--config', str(path),
                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    out, err = await asyncio.wait_for(proc.communicate(), 10)
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertIn(expected.encode(), err)
                    self.assertNotIn(KEY.encode(), out + err)
                    self.assertNotIn(b'Traceback', err)
        finally:
            listener.close()
            await listener.wait_closed()

    async def test_bind_failure_closes_provider_and_hides_os_details(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'gateway.local.json'
            path.write_text(json.dumps({'devices': {'dos-pc': DEVICE}, 'provider': 'mock'}))
            provider = AsyncMock()
            with patch.object(server, 'build_provider', return_value=provider), patch.object(
                    server.Gateway, 'start', side_effect=OSError(KEY)):
                with self.assertRaisesRegex(ConfigurationError, 'Cannot listen on port 1983') as error:
                    await server.run(path)
                self.assertNotIn(KEY, str(error.exception))
                provider.close.assert_awaited_once()

    async def test_cli_listener_overrides_conflicting_config(self):
        # Config points at an occupied port and unavailable IP; the CLI must win.
        listener = await asyncio.start_server(lambda r, w: w.close(), '127.0.0.1', 0)
        probe = await asyncio.start_server(lambda r, w: w.close(), '127.0.0.1', 0)
        port = probe.sockets[0].getsockname()[1]
        probe.close()
        await probe.wait_closed()
        try:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'gateway.json'
                path.write_text(json.dumps({'devices': {'dos-pc': DEVICE}, 'provider': 'mock',
                    'host': '192.0.2.1', 'port': listener.sockets[0].getsockname()[1]}))
                env = dict(os.environ, PYTHONPATH=str(ROOT / 'server/src'))
                proc = await asyncio.create_subprocess_exec(sys.executable, '-m', 'ai4dos.server',
                    '--config', str(path), '--host', '127.0.0.1', '--port', str(port),
                    env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                try:
                    ready = await asyncio.wait_for(proc.stdout.readline(), 10)
                    self.assertIn(('ready on port %s.' % port).encode(), ready)
                    reader, writer = await asyncio.open_connection('127.0.0.1', port)
                    from ai4dos.protocol import GREETING
                    self.assertEqual((await reader.readline()).decode().strip(), GREETING)
                    writer.close()
                    await writer.wait_closed()
                finally:
                    if proc.returncode is None:
                        import signal
                        proc.send_signal(signal.SIGINT)
                    await asyncio.wait_for(proc.communicate(), 10)
        finally:
            listener.close()
            await listener.wait_closed()

    async def test_actual_starter_ready_and_clean_exit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'gateway.local.json'
            path.write_text(json.dumps({'devices': {'dos-pc': DEVICE}, 'provider': 'mock', 'port': 0}))
            process = await asyncio.create_subprocess_exec(str(ROOT / 'start.sh'), '--config', str(path),
                cwd=folder, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                line = await asyncio.wait_for(process.stdout.readline(), 10)
                self.assertIn(b'AI4DOS gateway ready on port', line)
                import signal
                process.send_signal(signal.SIGINT)
                out, err = await asyncio.wait_for(process.communicate(), 10)
                self.assertEqual(process.returncode, 0)
                self.assertNotIn(b'Traceback', err)
                self.assertNotIn(KEY.encode(), line + out + err)
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
