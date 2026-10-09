import asyncio
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'server/src'))
from ai4dos.config import Settings
from ai4dos.protocol import GREETING

def extract(archive, destination):
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        z.extractall(destination)
        for entry in z.infolist():
            (destination/entry.filename).chmod(entry.external_attr >> 16 & 0o777)

async def main():
    result = {}
    spec = importlib.util.spec_from_file_location('packages', ROOT/'tools/package-release.py')
    packages = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(packages)
    with tempfile.TemporaryDirectory(prefix='AI4DOS delta ') as directory:
        directory = Path(directory).resolve()
        for target in packages.TARGETS:
            archive = packages.build(target, directory/'rebuild')
            released = ROOT/'dist'/archive.name
            assert released.read_bytes() == archive.read_bytes()
            out = directory/target
            extract(released, out)
            if target == 'dos':
                assert (out/'AI4DOS.EXE').read_bytes() == (ROOT/'release/inputs/AI4DOS.EXE').read_bytes()
                result[target] = 'CRC, deterministic rebuild, pinned EXE, 8.3 names, CRLF config: PASS'
                continue
            # Loading defaults must reject the user key placeholder without creating a listener.
            gateway = out/('config.local/gateway.json' if target=='docker' else 'server/gateway.local.json')
            data = json.loads(gateway.read_text())
            provider = gateway.parent/data['provider_config']
            assert provider.is_file()
            try:
                Settings.load(gateway)
            except (ValueError, TypeError):
                pass
            else:
                raise AssertionError('Unedited placeholder accepted')
            data.update(host='127.0.0.1', port=0, devices={'dos-pc': 'synthetic-local-test-key'})
            gateway.write_text(json.dumps(data))
            provider.write_text('PROVIDER=openrouter\nMODEL=openrouter/free\nAPI_KEY=SYNTHETIC_OFFLINE_DELTA_KEY\nREASONING=none\n')
            settings = Settings.load(gateway)
            assert settings.provider=='openrouter' and settings.port==0
            assert settings.api_key=='SYNTHETIC_OFFLINE_DELTA_KEY'
            assert settings.devices==data['devices']
            result[target] = 'Default config rejects placeholder; manual config editing + relative provider resolution: PASS'
            if target=='docker':
                subprocess.run(['docker','compose','config','--quiet'], cwd=out, check=True)
                env = dict(os.environ, AI4DOS_GATEWAY_CONFIG=str(gateway), AI4DOS_PROVIDER_CONFIG=str(provider))
                subprocess.run(['docker','compose','-f','portainer-stack.yml','config','--quiet'], cwd=out, env=env, check=True)
                result[target] += '; extracted Compose + Portainer schema: PASS'
            if target in ('macos','linux'):
                # Create fresh isolated venv; reuse already installed, locked local dependencies offline.
                subprocess.run([sys.executable,'-m','venv','--without-pip',str(out/'.venv')], check=True, capture_output=True)
                site = next((out/'.venv/lib').glob('python*/site-packages'))
                deps = next((ROOT/'.venv/lib').glob('python*/site-packages'))
                (site/'offline-test-dependencies.pth').write_text(str(deps)+'\n')
                proc = await asyncio.create_subprocess_exec(str(out/'start.sh'), cwd=directory,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                    env={k:v for k,v in os.environ.items() if not k.endswith('API_KEY') and k!='PYTHONPATH'})
                try:
                    line = await asyncio.wait_for(proc.stdout.readline(), 10)
                    assert b'AI4DOS gateway ready on port' in line, line
                    port = int(re.search(rb'ready on port (\d+)', line).group(1))
                    reader, writer = await asyncio.open_connection('127.0.0.1',port)
                    assert (await asyncio.wait_for(reader.readline(), 5)).strip()==GREETING.encode()
                    writer.close()
                    await writer.wait_closed()
                    proc.send_signal(signal.SIGINT)
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), 10)
                    assert proc.returncode==0, stderr
                    assert b'Traceback' not in stdout+stderr
                    result[target] += '; fresh ZIP launcher from different directory, actual TCP listener, SIGINT exit 0: PASS on macOS; locked dependencies reused offline'
                finally:
                    if proc.returncode is None:
                        proc.kill()
                        await proc.wait()
        for target, value in result.items():
            print(target, value)

if __name__ == '__main__':
    asyncio.run(main())
