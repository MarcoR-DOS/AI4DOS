#!/usr/bin/env python3
"""Mandatory offline provider/gateway/package gate; live requires --live-config."""
import argparse
import asyncio
from contextlib import ExitStack, contextmanager
import hashlib
import importlib.util
import ipaddress
import json
import os
import re
import zipfile
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'server/src'), str(ROOT/'tools')]
PROVIDERS = ('openai', 'nvidia', 'openrouter', 'gemini', 'anthropic', 'mistral',
             'openai-compatible', 'mock')
# Existing contract suites, including the existing host-client label/wire tests.
SUITES = ('test_providers', 'test_provider_regressions', 'test_anthropic_provider',
          'test_provider_labels', 'test_gateway', 'test_preauth', 'test_startup',
          'test_release_packages', 'test_release_gate')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@contextmanager
def offline_network():
    # Fail closed on accidental provider/DNS access in contract tests.
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_resolve = socket.getaddrinfo
    def allowed(host):
        if host == 'localhost': return
        try:
            if ipaddress.ip_address(host).is_loopback: return
        except ValueError: pass
        raise RuntimeError('External networking forbidden by offline release gate')
    def connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6): allowed(address[0])
        return original_connect(sock, address)
    def connect_ex(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6): allowed(address[0])
        return original_connect_ex(sock, address)
    def resolve(host, *args, **kwargs):
        allowed(host)
        return original_resolve(host, *args, **kwargs)
    with patch.object(socket.socket, 'connect', connect), patch.object(socket.socket, 'connect_ex', connect_ex), patch.object(socket, 'getaddrinfo', resolve):
        yield


def offline_suite():
    suite = unittest.TestSuite()
    for name in SUITES:
        selected = unittest.defaultTestLoader.discover(str(ROOT/'tests'), name+'.py')
        if not selected.countTestCases(): raise RuntimeError('Required suite missing or empty')
        suite.addTests(selected)
    with offline_network():
        result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful(): raise RuntimeError('Offline contract suite failed')
    if result.skipped: raise RuntimeError('Required release test skipped')
    return {'status':'OFFLINE PASS', 'tests':result.testsRun, 'skipped':len(result.skipped)}


SECRET_PATTERNS = re.compile(rb'(?:sk-(?:proj-|or-v1-|ant-)?[A-Za-z0-9_-]{20,}|nvapi-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')


def has_secret(data):
    return SECRET_PATTERNS.search(data) is not None


def secret_hygiene(archives):
    paths = subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).split(b'\0')
    count = 0
    for path in paths:
        if not path: continue
        data = (ROOT/os.fsdecode(path)).read_bytes()
        if has_secret(data): count += 1
    for archive in archives:
        with zipfile.ZipFile(archive) as z:
            count += sum(has_secret(z.read(name)) for name in z.namelist())
    if count: raise RuntimeError('Credential pattern found; values are never printed')
    return {'status':'PASS', 'credential_pattern_hits':0}


async def live(config):
    import httpx
    from ai4dos.config import Settings, build_provider
    from ai4dos.server import Gateway
    from ai4dos.provider import ProviderError
    import logging
    for name in ("openai", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
    from ai4dos.session import Session
    result = {'requests':0, 'status':'FAIL'}
    settings = Settings.load(config)
    result.update(provider=settings.provider, model=settings.model)
    if settings.provider in ('mock', 'openai-compatible'):
        raise ValueError('Live mode only accepts external providers')
    if settings.max_output_tokens > 256:
        raise ValueError('Live config must explicitly limit MAX_OUTPUT_TOKENS to <=256')
    async def request(req):
        if result['requests']: raise RuntimeError('Live request budget exhausted')
        result['requests'] += 1
    async def response(res):
        result['http_status'] = res.status_code
    def client():
        return httpx.AsyncClient(trust_env=False, timeout=45,
            event_hooks={'request':[request], 'response':[response]})
    with ExitStack() as stack:
        for name in ('provider', 'gemini_provider', 'anthropic_provider'):
            stack.enter_context(patch('ai4dos.'+name+'.make_http_client', client))
        try:
            provider = build_provider(settings)
        except (ValueError, FileNotFoundError):
            result.update(status='LIVE NOT AVAILABLE', reason='key/config unavailable')
            return result
    gateway = Gateway(settings, provider)
    class Writer:
        frames = []
        def write(self, data): self.frames.append(data.decode().strip())
        async def drain(self): pass
    writer = Writer()
    try:
        await asyncio.wait_for(gateway.respond(writer, Session(), 'Reply with exactly OK.'), 60)
        frames = writer.frames
        errors = [f.split()[1] for f in frames if f.startswith('ERROR ')]
        if errors:
            code = errors[0]
            result.update(error=code, status='LIVE NOT AVAILABLE' if code == 'UPSTREAM_MODEL' and result.get('http_status') == 404 else 'FAIL')
        elif 'END' in frames and any(f.startswith('DATA ') for f in frames):
            result['status'] = 'LIVE PASS'
    except ProviderError as exc:
        result.update(error=exc.code, status='LIVE NOT AVAILABLE' if exc.code == 'UPSTREAM_MODEL' and result.get('http_status') == 404 else 'FAIL')
    finally: await gateway.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live-config', type=Path, action='append', default=[],
                        help='Explicit private gateway JSON; one request per config, no retries')
    parser.add_argument('--output', type=Path, default=ROOT/'dist')
    args = parser.parse_args()
    # Prevent inherited runtime settings/keys from influencing the offline gate.
    live_environment = dict(os.environ)
    for key in list(os.environ):
        if key.startswith('AI4DOS_') or key.endswith('API_KEY') or key in ('API_KEY', 'OPENAI_LOG'):
            os.environ.pop(key)
    report = {'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'offline':{'status':'FAIL'}, 'providers':{}, 'live':[], 'packages':{}}
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        report['stage'] = 'host-test-client'
        # Same minimal host test binary used by existing label/gateway tests.
        # No DOS build, UI work or runtime package change.
        (ROOT/'client/build').mkdir(exist_ok=True)
        subprocess.run(['cc','-std=c89','-Wall','-Wextra','-Werror','-Iclient/include',
            *['client/src/'+n+'.c' for n in ('main','charset','config','l10n','protocol','sha256')],
            'tests/native_transport.c','-o','client/build/ai4dos-host'],cwd=ROOT,check=True)
        report['stage'] = 'contracts'
        report['contracts'] = offline_suite()
        report['providers'] = {p:{'offline':'OFFLINE PASS', 'live':'LIVE NOT AVAILABLE',
                                 'reason':'not requested'} for p in PROVIDERS}
        report['stage'] = 'reproducible-packages'
        packages = module('release_packages', ROOT/'tools/package-release.py')
        packages.verify_dos_input(ROOT)
        with tempfile.TemporaryDirectory(prefix='ai4dos-repro-') as temp:
            for target in packages.TARGETS:
                rebuilt = packages.build(target, Path(temp))
                if target == 'dos':
                    archive = args.output/rebuilt.name
                    if archive.exists() and archive.read_bytes() != rebuilt.read_bytes():
                        raise RuntimeError('Existing DOS ZIP differs from pinned inputs')
                    if not archive.exists(): archive.write_bytes(rebuilt.read_bytes())
                else:
                    archive = packages.build(target, args.output)
                    if archive.read_bytes() != rebuilt.read_bytes():
                        raise RuntimeError('Non-reproducible archive')
                report['packages'][target] = {'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
                    'archive':archive.name, 'reproducible':True}
        report['stage'] = 'secret-hygiene'
        report['secret_hygiene'] = secret_hygiene([args.output/p['archive'] for p in report['packages'].values()])
        from validate_gateway_packages import validate
        report['stage'] = 'package-smokes'
        report['smokes'] = asyncio.run(validate(args.output))
        subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
        report['offline'] = {'status':'OFFLINE PASS'}
        report['stage'] = 'live-smokes'
        seen = set()
        for config in args.live_config:
            from ai4dos.config import Settings
            name = Settings.load(config).provider
            if name in seen: raise ValueError('Duplicate live provider')
            seen.add(name)
        for config in args.live_config:
            # Avoid duplicate billable requests for the same provider.
            from ai4dos.config import Settings
            name = Settings.load(config).provider
            with patch.dict(os.environ, live_environment, clear=True):
                result = asyncio.run(live(config))
            report['live'].append(result)
            report['providers'][name]['live'] = result['status']
            report['providers'][name]['reason'] = result.get('reason', result.get('error',''))
            if result['status'] == 'FAIL': raise RuntimeError('Live smoke failed')
    except Exception as exc:
        # No raw exceptions/config/provider bodies: these may contain credentials.
        report['failure_type'] = type(exc).__name__
        print('RELEASE GATE FAIL ('+type(exc).__name__+')',file=sys.stderr)
        status = 1
    else:
        report['stage'] = 'complete'
        status = 0
        print('RELEASE GATE: OFFLINE PASS; live availability is reported separately')
    (args.output/'release-gate.json').write_text(json.dumps(report,indent=2)+'\n')
    for name, result in report['providers'].items():
        print(name+': '+result['offline']+' / '+result['live'])
    return status


if __name__ == '__main__':
    sys.exit(main())
