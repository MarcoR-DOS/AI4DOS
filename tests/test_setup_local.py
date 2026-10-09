import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LocalSetupTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX Docker wrapper")
    def test_docker_wrapper_leaves_environment_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'tools').mkdir()
            shutil.copy2(ROOT / 'tools/setup-docker.sh', root / 'tools/setup-docker.sh')
            binary = root / 'bin'
            binary.mkdir()
            docker = binary / 'docker'
            docker.write_text('#!/bin/sh\nexit "${FAKE_DOCKER_EXIT:-0}"\n')
            docker.chmod(0o755)
            env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ['PATH'])
            original = 'API_KEY=synthetic-provider-key\n'
            (root / '.env').write_text(original)
            result = subprocess.run(['sh', str(root / 'tools/setup-docker.sh'),
                                     '--server-address', '192.0.2.10'], env=env, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            content = (root / '.env').read_text()
            self.assertTrue(content.startswith(original))
            self.assertEqual(content, original)
            self.assertNotIn(b'synthetic-provider-key', result.stdout + result.stderr)
            (root / '.env').write_text(original)
            result = subprocess.run(['sh', str(root / 'tools/setup-docker.sh')],
                                     env=dict(env, FAKE_DOCKER_EXIT='1'), capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((root / '.env').read_text(), original)

    @unittest.skipIf(os.name == "nt", "Docker setup uses POSIX/WSL file permissions")
    def test_docker_pair_permissions_and_manual_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'tools').mkdir()
            (root / 'server').mkdir()
            shutil.copy2(ROOT / 'tools/setup-local.py', root / 'tools/setup-local.py')
            shutil.copy2(ROOT / 'server/provider.example.cfg', root / 'server/provider.example.cfg')
            result = subprocess.run([sys.executable, str(root / 'tools/setup-local.py'),
                                     '--docker', '--server-address', '192.0.2.10'], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            config = root / 'config.local'
            gateway = json.loads((config / 'gateway.json').read_text())
            self.assertEqual(gateway['host'], '0.0.0.0')
            self.assertEqual(gateway['provider_config'], 'provider.cfg')
            self.assertFalse((config / 'AI4DOS.CFG').exists())
            self.assertEqual(gateway['devices'], {'dos-pc': '<KEY>'})
            self.assertNotIn(b'SECRET=', result.stdout)
            if os.name != 'nt':
                self.assertEqual(config.stat().st_mode & 0o777, 0o700)
                self.assertEqual((config / 'gateway.json').stat().st_mode & 0o777, 0o444)
                self.assertEqual((config / 'provider.cfg').stat().st_mode & 0o777, 0o444)

    def test_pair_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='AI4DOS setup ') as folder:
            root = Path(folder)
            for directory in ('tools', 'server', 'client'):
                (root / directory).mkdir()
            shutil.copy2(ROOT / 'tools/setup-local.py', root / 'tools/setup-local.py')
            shutil.copy2(ROOT / 'server/provider.example.cfg', root / 'server/provider.example.cfg')
            command = [sys.executable, str(root / 'tools/setup-local.py'), '--server-address', '127.0.0.1']
            bad = subprocess.run(command[:-1] + ['0.0.0.0'], capture_output=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertFalse((root / 'server/gateway.local.json').exists())
            existing = root / 'client/AI4DOS.CFG'
            existing.write_bytes(b'user owned DOS config')
            result = subprocess.run(command, cwd=folder, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            gateway = json.loads((root / 'server/gateway.local.json').read_text())
            self.assertEqual(gateway['devices'], {'dos-pc': '<KEY>'})
            self.assertEqual(existing.read_bytes(), b'user owned DOS config')
            self.assertNotIn(b'SECRET=', result.stdout)
            (root / 'client/AI4DOS.CFG').write_bytes(b'user owned DOS config')
            paths = [root / 'server/gateway.local.json', root / 'server/provider.local.cfg', root / 'client/AI4DOS.CFG']
            before = [p.read_bytes() for p in paths]
            again = subprocess.run(command, capture_output=True)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual(before, [p.read_bytes() for p in paths])
            self.assertNotIn(b'Traceback', again.stderr)


    @unittest.skipIf(os.name == "nt", "POSIX Docker wrapper")
    def test_docker_wrapper_uses_shipped_configs_without_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'tools').mkdir()
            shutil.copy2(ROOT/'tools/setup-docker.sh', root/'tools/setup-docker.sh')
            (root/'config.local').mkdir()
            (root/'bin').mkdir()
            docker = root/'bin/docker'
            docker.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\n')
            docker.chmod(0o755)
            originals = {'config.local/gateway.json': b'user-owned gateway',
                         'config.local/provider.cfg': b'user-owned provider'}
            for name, data in originals.items():
                (root/name).write_bytes(data)
            env = dict(os.environ, PATH=str(root/'bin')+os.pathsep+os.environ['PATH'],
                       CALL_LOG=str(root/'calls'))
            result = subprocess.run(['sh',str(root/'tools/setup-docker.sh')],env=env,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual((root/'calls').read_text().splitlines(),['compose build gateway'])
            self.assertEqual({name:(root/name).read_bytes() for name in originals}, originals)
