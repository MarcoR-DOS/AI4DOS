"""Runtime contents, platform isolation and byte reproducibility; offline."""
import importlib.util
import json
import shutil
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('packages', ROOT/'tools/package-release.py')
packages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packages)


class ReleasePackages(unittest.TestCase):
    def test_all_targets_reproducible_and_documentation_free(self):
        with tempfile.TemporaryDirectory() as folder:
            for target in packages.TARGETS:
                with self.subTest(target=target):
                    a = packages.build(target, Path(folder)/'a')
                    b = packages.build(target, Path(folder)/'b')
                    self.assertEqual(a.read_bytes(), b.read_bytes())
                    with zipfile.ZipFile(a) as z:
                        self.assertIsNone(z.testzip())
                        names = set(z.namelist())
                        self.assertEqual(names, set(packages.package_files(target).values()) | set(packages.shipped_templates(target)))
                        for name in names:
                            lower = name.lower()
                            self.assertNotIn('readme', lower)
                            self.assertNotIn('start-here', lower)
                            self.assertNotIn('quickstart', lower)
                            self.assertFalse(lower.startswith('docs/'))
                            self.assertNotIn('example', lower)
                            self.assertNotEqual(lower, '.env')
                            self.assertNotIn(name, ('tools/setup-local.py', 'tools/setup-docker.sh'))
                            if '.local' in lower:
                                self.assertIn(name, packages.shipped_templates(target))
                        self.assertIn('LICENSE.TXT' if target == 'dos' else 'LICENSE', names)
                        if target == 'dos':
                            self.assertEqual(names, {'AI4DOS.EXE','AI4DOS.CFG','LICENSE.TXT',
                                'NOTICES.TXT','WATCOM.TXT','VERSION.TXT'})
                            self.assertNotIn(b'\n', z.read('AI4DOS.CFG').replace(b'\r\n', b''))
                            self.assertTrue(z.read('AI4DOS.EXE').startswith(b'MZ'))
                            for name in names:
                                base, ext = name.split('.')
                                self.assertLessEqual(len(base), 8)
                                self.assertLessEqual(len(ext), 3)
                        else:
                            self.assertIn('server/src/ai4dos/server.py', names)
                            self.assertNotIn('AI4DOS.EXE', names)
                            self.assertEqual('START.BAT' in names, target == 'windows')
                            self.assertEqual('start.sh' in names, target in ('macos','linux'))
                            self.assertEqual('Dockerfile' in names, target == 'docker')
                            self.assertNotIn('.env.example', names)
                            if 'start.sh' in names:
                                self.assertTrue((z.getinfo('start.sh').external_attr >> 16) & 0o111)
                            if target == 'docker':
                                # Verify every current Docker COPY input is present.
                                for name in ('server/requirements.txt','server/requirements-lock.txt',
                                             'tools/docker-healthcheck.py'):
                                    self.assertIn(name, names)

    def test_packages_work_without_private_license_record_or_git_history(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve() / 'repo'
            manifest = json.loads((ROOT/'release/inputs/dos-build.json').read_text())
            sources = set(manifest['sha256']) | {'release/inputs/dos-build.json'}
            for target in packages.TARGETS:
                sources.update(packages.package_files(target))
                sources.update(packages.shipped_templates(target).values())
            self.assertNotIn('LICENSE-PENDING.md', sources)
            for source in sources:
                path = root/source
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/source, path)
            self.assertFalse((root/'.git').exists())
            for target in packages.TARGETS:
                with self.subTest(target=target), zipfile.ZipFile(
                        packages.build(target, Path(folder)/'archives', root)) as z:
                    self.assertNotIn('LICENSE-PENDING.md', z.namelist())
                    self.assertNotIn('LIC-STAT.TXT', z.namelist())
                    self.assertEqual(z.read('LICENSE.TXT' if target == 'dos' else 'LICENSE'),
                                     (ROOT/'LICENSE').read_bytes())
                    notices = z.read('NOTICES.TXT' if target == 'dos' else 'THIRD_PARTY_NOTICES.md')
                    self.assertNotIn(b'LICENSE-PENDING.md', notices)
                    self.assertIn(b'GPL-3.0-or-later', notices)
                    if target == 'dos':
                        self.assertEqual(z.read('WATCOM.TXT'),
                                         (ROOT/'third_party/WATCOM-LICENSE.txt').read_bytes())

    def test_missing_input_fails_before_writing_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'output'
            with self.assertRaises(ValueError):
                packages.build('dos', output, Path(folder)/'missing')
            self.assertFalse(output.exists())


    def test_shipped_configs_are_editable_and_resolve_provider(self):
        with tempfile.TemporaryDirectory() as folder:
            for target in packages.TARGETS[1:]:
                with self.subTest(target=target), zipfile.ZipFile(packages.build(target, Path(folder))) as z:
                    gateway = 'config.local/gateway.json' if target == 'docker' else 'server/gateway.local.json'
                    provider = 'config.local/provider.cfg' if target == 'docker' else 'server/provider.local.cfg'
                    config = json.loads(z.read(gateway))
                    self.assertEqual(config['devices'], {'dos-pc': '<KEY>'})
                    self.assertEqual(str(Path(gateway).parent / config['provider_config']), provider)
                    self.assertIn(b'API_KEY=\n', z.read(provider))
                    self.assertTrue((z.getinfo(gateway).external_attr >> 16) & 0o200)
                    if target == 'docker':
                        self.assertEqual(config['host'], '0.0.0.0')
                        self.assertNotIn('.env', z.namelist())
                        for stack in ('docker-compose.yml', 'portainer-stack.yml'):
                            self.assertNotIn(b'API_KEY', z.read(stack))
                        self.assertTrue((z.getinfo(provider).external_attr >> 16) & 0o004)
                    else:
                        self.assertEqual(z.getinfo(gateway).external_attr >> 16 & 0o777, 0o600)

    def test_private_configs_cannot_enter_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve() / 'repo'
            for source in (*packages.package_files('docker'), *packages.shipped_templates('docker').values()):
                path = root/source
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/source, path)
            for name in ('server/gateway.local.json', 'server/provider.local.cfg',
                         'config.local/gateway.json', 'config.local/provider.cfg', '.env'):
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('SYNTHETIC_PRIVATE_SENTINEL')
            with zipfile.ZipFile(packages.build('docker', Path(folder)/'output', root)) as z:
                self.assertTrue(all(b'SYNTHETIC_PRIVATE_SENTINEL' not in z.read(n) for n in z.namelist()))

    def test_changed_dos_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()/'repo'
            manifest = json.loads((ROOT/'release/inputs/dos-build.json').read_text())
            for source in (*manifest['sha256'], 'release/inputs/dos-build.json'):
                path = root/source
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/source, path)
            packages.verify_dos_input(root)
            (root/'client/src/main.c').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'DOS release input changed'):
                packages.verify_dos_input(root)


    def test_provider_template_without_hints_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'missing provider values'):
            packages.verify_template('server/provider.example.cfg', b'PROVIDER=openrouter\nAPI_KEY=\n')

    def test_populated_example_credentials_fail_closed(self):
        for source, data in (
            ('server/provider.example.cfg', b'API_KEY=SYNTHETIC_PRIVATE_SENTINEL\n'),
            ('client/AI4DOS.CFG.example', b'SECRET=SYNTHETIC_PRIVATE_SENTINEL\n'),
            ('server/gateway.example.json', b'{"devices":{"dos-pc":"SYNTHETIC_PRIVATE_SENTINEL"}}')
        ):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError,'non-placeholder credentials'):
                packages.verify_template(source,data)

    def test_product_version_mismatch_fails_before_packaging(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve() / 'repo'
            for source in (*packages.package_files('docker'), *packages.shipped_templates('docker').values()):
                path = root/source
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/source, path)
            (root/'VERSION').write_text('0.1.0-beta.2\n')
            with self.assertRaisesRegex(ValueError, 'gateway product version differs'):
                packages.build('docker', Path(folder)/'output', root)
            self.assertFalse((Path(folder)/'output').exists())
