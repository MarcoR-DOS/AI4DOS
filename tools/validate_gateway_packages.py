"""Fresh ZIP delta smokes; no provider requests, no native Windows/Linux claim."""
import asyncio
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SECRET = 'synthetic-release-device-key'


def extract(archive, out):
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None: raise RuntimeError('ZIP CRC failed')
        for entry in z.infolist():
            if Path(entry.filename).is_absolute() or '..' in Path(entry.filename).parts:
                raise RuntimeError('Unsafe ZIP path')
        z.extractall(out)
        for entry in z.infolist():
            (out/entry.filename).chmod(entry.external_attr >> 16 & 0o777)
        # Every shipped module must be the current source, including adapter fixes.
        for name in z.namelist():
            if name.startswith('server/src/') and z.read(name) != (ROOT/name).read_bytes():
                raise RuntimeError('Stale gateway module')


def configure(out, docker=False):
    cfg = out/('config.local/gateway.json' if docker else 'server/gateway.local.json')
    data = json.loads(cfg.read_text())
    data.update(host='0.0.0.0' if docker else '127.0.0.1', port=1983 if docker else 0,
                devices={'release-test':SECRET})
    cfg.write_text(json.dumps(data))
    (cfg.parent/data['provider_config']).write_text('PROVIDER=mock\nMODEL=mock\nAPI_KEY=\nREASONING=none\n')
    return cfg


async def mock_chat(port):
    from ai4dos.protocol import GREETING, unescape_data
    reader, writer = await asyncio.open_connection('127.0.0.1',port)
    async def read(): return (await asyncio.wait_for(reader.readline(),5)).decode().strip()
    async def send(line):
        writer.write((line+'\r\n').encode()); await writer.drain()
    try:
        assert await read() == GREETING
        await send('HELLO release-test')
        challenge = (await read()).split()
        assert challenge[0] == 'CHALLENGE'
        digest = hmac.new(SECRET.encode(),challenge[1].encode(),hashlib.sha256).hexdigest()
        await send('AUTH '+digest)
        assert await read() == 'OK AUTH'
        await send('NEW')
        assert (await read()).startswith('SESSION ')
        await send('MSG release-delta')
        assert await read() == 'BEGIN'
        text = []
        while True:
            line = await read()
            if line == 'END': break
            assert line.startswith('DATA ')
            text.append(unescape_data(line[5:]))
        assert ''.join(text) == 'Test reply: release-delta'
    finally:
        writer.close(); await writer.wait_closed()


async def launcher(out, cwd):
    subprocess.run([sys.executable,'-m','venv','--without-pip',str(out/'.venv')],check=True,capture_output=True)
    site = next((out/'.venv/lib').glob('python*/site-packages'))
    # Reuse installed dependencies only; never import gateway source from the repo.
    spec = importlib.util.find_spec('httpx')
    (site/'offline-test-dependencies.pth').write_text(str(Path(spec.origin).parents[1])+'\n')
    proc = await asyncio.create_subprocess_exec(str(out/'start.sh'),cwd=cwd,
        stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,
        env={k:v for k,v in os.environ.items() if k != 'PYTHONPATH'})
    try:
        line = await asyncio.wait_for(proc.stdout.readline(),10)
        port = int(re.search(rb'ready on port (\d+)',line).group(1))
        await mock_chat(port)
        proc.send_signal(signal.SIGINT)
        stdout, stderr = await asyncio.wait_for(proc.communicate(),10)
        assert proc.returncode == 0 and b'Traceback' not in stdout+stderr
        assert SECRET.encode() not in stdout+stderr
    finally:
        if proc.returncode is None:
            proc.kill(); await proc.wait()


async def docker(out):
    # Unique names, cleanup on every path; no host ports and no external network.
    suffix = str(os.getpid())
    image = 'ai4dos-release-gate:'+suffix
    name = 'ai4dos-release-gate-'+suffix
    def run(args):
        return subprocess.run(['docker',*args],check=True,capture_output=True,text=True,timeout=300).stdout
    run(['info','--format','{{.ServerVersion}}'])
    run(['build','--pull=false','-t',image,str(out)])
    cfg = configure(out,True)
    provider = cfg.parent/'provider.cfg'
    cfg.chmod(0o644); provider.chmod(0o644)
    try:
        run(['run','-d','--name',name,'--network','none','--read-only',
             '--cap-drop','ALL','--security-opt','no-new-privileges:true',
             '--mount',f'type=bind,src={cfg},dst=/config/gateway.json,readonly',
             '--mount',f'type=bind,src={provider},dst=/config/provider.cfg,readonly',
             '--mount',f'type=bind,src={Path(__file__)},dst=/tmp/package_smoke.py,readonly',image])
        for _ in range(40):
            test = subprocess.run(['docker','exec',name,'python','/app/tools/docker-healthcheck.py'],capture_output=True)
            if test.returncode == 0: break
            await asyncio.sleep(0.5)
        else: raise RuntimeError('Docker healthcheck failed')
        # Same authenticated wire smoke executes inside the isolated container.
        run(['exec',name,'python','-c',
             'import sys,asyncio; sys.path.insert(0,"/tmp"); from package_smoke import mock_chat; asyncio.run(mock_chat(1983))'])
        state = json.loads(run(['inspect',name]))[0]
        assert state['Config']['User'] == '10001:10001'
        assert state['HostConfig']['NetworkMode'] == 'none'
        assert state['HostConfig']['ReadonlyRootfs']
        assert all(not m['RW'] for m in state['Mounts'])
        assert SECRET not in run(['logs',name])
        # Validate the shipped Portainer/Compose syntax without deploying it.
        for stack in ('docker-compose.yml','portainer-stack.yml'):
            env = dict(os.environ,AI4DOS_GATEWAY_CONFIG=str(cfg),AI4DOS_PROVIDER_CONFIG=str(provider))
            subprocess.run(['docker','compose','-f',str(out/stack),'config','--quiet'],env=env,check=True,capture_output=True)
    finally:
        subprocess.run(['docker','rm','-f',name],capture_output=True)
        subprocess.run(['docker','image','rm',image],capture_output=True)


async def validate(dist):
    results = {}
    with tempfile.TemporaryDirectory(prefix='ai4dos-zip-smoke-') as folder:
        temp = Path(folder)
        for target, filename in (('windows','Windows'),('macos','macOS'),('linux','Linux'),('docker','Docker')):
            out = temp/target
            extract(dist/('AI4DOS-Server-'+filename+'.zip'),out)
            # Import each ZIP in a fresh subprocess, with all source paths isolated.
            env = dict(os.environ,PYTHONPATH=str(out/'server/src'),PYTHONDONTWRITEBYTECODE='1')
            code = ('import pathlib,importlib,ai4dos; '
                    'assert pathlib.Path(ai4dos.__file__).resolve().is_relative_to(pathlib.Path.cwd()); '
                    '[importlib.import_module("ai4dos."+p.stem) for p in pathlib.Path("server/src/ai4dos").glob("*.py")]')
            subprocess.run([sys.executable,'-B','-c',code],cwd=out,env=env,check=True,capture_output=True)
            configure(out, target == 'docker')
            if target == 'windows':
                starter = (out/'START.BAT').read_text()
                assert '%~dp0' in starter and '-m ai4dos.server' in starter
                results[target] = 'PASS: current modules/import/config/starter contract on host; no native Windows run'
            elif target in ('macos','linux'):
                if os.name == 'nt': raise RuntimeError('POSIX ZIP launcher requires POSIX host')
                subprocess.run(['sh','-n',str(out/'start.sh')],check=True)
                await launcher(out,temp)
                results[target] = 'PASS: fresh ZIP launcher + authenticated Mock/END + clean exit on '+sys.platform+'; host dependencies reused'
            else:
                await docker(out)
                results[target] = 'PASS: ZIP image/healthcheck/authenticated Mock/END/UID10001/read-only/network-none/Compose+Portainer syntax'
            print(target+': '+results[target],flush=True)
    return results
