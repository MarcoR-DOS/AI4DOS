#!/usr/bin/env python3
"""Build deterministic runtime ZIPs; include only secret-free shipped config templates."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ('dos', 'windows', 'macos', 'linux', 'docker')
# Source list is explicit: a stray local Python file must never enter a release.
MODULES = ('__init__', 'anthropic_provider', 'compatible_provider', 'config',
           'gemini_provider', 'openai_provider', 'output', 'protocol', 'provider',
           'server', 'session', 'textfilter')
LEGAL = {'VERSION': 'VERSION', 'LICENSE': 'LICENSE', 'THIRD_PARTY_NOTICES.md': 'THIRD_PARTY_NOTICES.md'}
SERVER = {**LEGAL, **{f'server/src/ai4dos/{n}.py': f'server/src/ai4dos/{n}.py' for n in MODULES},
          **{f'server/{n}': f'server/{n}' for n in ('requirements.txt', 'requirements-lock.txt')}}


def package_files(target):
    if target == 'dos':
        return {'VERSION': 'VERSION.TXT', 'LICENSE': 'LICENSE.TXT', 'THIRD_PARTY_NOTICES.md': 'NOTICES.TXT',
                'release/inputs/AI4DOS.EXE': 'AI4DOS.EXE',
                'client/AI4DOS.CFG.example': 'AI4DOS.CFG',
                'third_party/WATCOM-LICENSE.txt': 'WATCOM.TXT'}
    files = dict(SERVER)
    if target == 'windows':
        files['START.BAT'] = 'START.BAT'
    elif target in ('macos', 'linux'):
        files['start.sh'] = 'start.sh'
    elif target == 'docker':
        for name in ('Dockerfile', 'docker-compose.yml', 'portainer-stack.yml', '.dockerignore',
                     'tools/docker-healthcheck.py'):
            files[name] = name
    else:
        raise ValueError('unknown package target')
    return files


def shipped_templates(target):
    # Destination -> reviewed repository example, never a user's local config.
    if target == 'dos':
        return {}
    if target == 'docker':
        return {'config.local/gateway.json': 'server/gateway.example.json',
                'config.local/provider.cfg': 'server/provider.example.cfg'}
    return {'server/gateway.local.json': 'server/gateway.example.json',
            'server/provider.local.cfg': 'server/provider.example.cfg'}


def read_input(root, source):
    path = root / source
    if not path.is_file() or path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('missing or symlinked package input: ' + source)
    return path.read_bytes()


def verify_template(source, data):
    # A reviewed example remains a release input only while it contains no key.
    if source == 'server/gateway.example.json':
        values = json.loads(data)
        if values.get('devices') != {'dos-pc': '<KEY>'} or any(
                values.get(name) for name in ('api_key', 'api_key_file')):
            raise ValueError('non-placeholder credentials in release template: ' + source)
    elif source.endswith('.example.cfg') or source == 'client/AI4DOS.CFG.example':
        for line in data.decode('utf-8').splitlines():
            name, separator, value = line.partition('=')
            if separator and name.strip() in ('API_KEY', 'API_KEY_FILE', 'SECRET'):
                expected = '<KEY>' if name.strip() == 'SECRET' else ''
                if value.strip() != expected:
                    raise ValueError('non-placeholder credentials in release template: ' + source)
        if source.startswith('server/provider.'):
            hints = b'# Provider values:\n# openai\n# anthropic\n# gemini\n# mistral\n# nvidia\n# openrouter\n# openai-compatible\n'
            if hints not in data:
                raise ValueError('missing provider values in release template: ' + source)


def verify_dos_input(root):
    manifest = json.loads(read_input(root, 'release/inputs/dos-build.json'))
    for source, expected in manifest['sha256'].items():
        if hashlib.sha256(read_input(root, source)).hexdigest() != expected:
            raise ValueError('DOS release input changed; rebuild and validate before updating provenance: ' + source)


def build(target, output, root=ROOT):
    version = read_input(root, 'VERSION').decode('ascii').strip()
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?', version):
        raise ValueError('invalid product version in VERSION')
    if target == 'dos':
        if version.encode('ascii') not in read_input(root, 'release/inputs/AI4DOS.EXE'):
            raise ValueError('DOS binary product version differs from VERSION; rebuild first')
    else:
        source_version = re.search(r'__version__ = "([^"]+)"',
                                  read_input(root, 'server/src/ai4dos/__init__.py').decode('utf-8'))
        if source_version is None or source_version.group(1) != version:
            raise ValueError('gateway product version differs from VERSION')
    files = {destination: source for source, destination in package_files(target).items()}
    templates = shipped_templates(target)
    files.update(templates)
    if target == 'dos':
        verify_dos_input(root)
    # Preflight before creating output. Symlinks must not capture external/private files.
    contents = []
    for destination, source in sorted(files.items()):
        data = read_input(root, source)
        verify_template(source, data)
        if target == 'dos' and destination == 'AI4DOS.CFG':
            data = data.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
        if destination == 'config.local/gateway.json':
            config = json.loads(data)
            config.update(host='0.0.0.0', port=1983, provider_config='provider.cfg')
            data = (json.dumps(config, indent=2) + '\n').encode('ascii')
        if source == 'THIRD_PARTY_NOTICES.md':
            # Notice links point to central documentation, absent from runtime ZIPs.
            data = data.replace(b'](third_party/', b'](https://github.com/MarcoR-DOS/AI4DOS/blob/main/third_party/')
        contents.append((destination, data))
    output.mkdir(parents=True, exist_ok=True)
    name = 'AI4DOS-DOS.zip' if target == 'dos' else f'AI4DOS-Server-{target.capitalize() if target != "macos" else "macOS"}.zip'
    archive = output / name
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for destination, data in contents:
            entry = zipfile.ZipInfo(destination, (1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.compress_type = zipfile.ZIP_DEFLATED
            # Docker config mounts must be readable by container UID 10001.
            # Shipped files contain placeholders only and remain editable on the host.
            mode = 0o644
            if destination.endswith('.sh'):
                mode = 0o755
            elif destination in templates and target != 'docker':
                mode = 0o600
            entry.external_attr = (0o100000 | mode) << 16
            z.writestr(entry, data, compresslevel=9)
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', choices=(*TARGETS, 'all'))
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    for target in TARGETS if args.target == 'all' else (args.target,):
        print(build(target, args.output))


if __name__ == '__main__':
    main()
