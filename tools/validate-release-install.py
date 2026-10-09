import asyncio
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'server/src'))
from ai4dos.config import Settings
from ai4dos.provider import MockProvider
from ai4dos.server import Gateway

def extract(path, out):
    with zipfile.ZipFile(path) as z:
        z.extractall(out)
        for entry in z.infolist():
            (out/entry.filename).chmod(entry.external_attr >> 16 & 0o777)

async def dos(directory):
    out = directory/'dos'
    extract(ROOT/'dist/AI4DOS-DOS.zip', out)
    driver = ROOT/'client/build/NE2K.COM'
    assert hashlib.sha256(driver.read_bytes()).hexdigest()=='f95b36199a47bf7e6eb03cb9474e97d50cb9c23de08996a036bb525599e0b9f2'
    shutil.copyfile(driver, out/'NE2K.COM')
    class RecordedMock(MockProvider):
        calls = 0
        async def stream(self, messages):
            self.calls += 1
            assert messages[-1].text=='release-delta'
            async for text in super().stream(messages):
                yield text
    provider = RecordedMock()
    secret = secrets.token_hex(32)
    gateway = Gateway(Settings(host='127.0.0.1',port=0, devices={'dos-pc':secret}), provider)
    listener = await gateway.start()
    port = listener.sockets[0].getsockname()[1]
    proc = None
    try:
        cfg = (out/'AI4DOS.CFG').read_text().replace('SERVER=127.0.0.1','SERVER=10.0.2.2').replace('PORT=1983',f'PORT={port}').replace('SECRET=<KEY>',f'SECRET={secret}')
        (out/'AI4DOS.CFG').write_bytes(cfg.replace('\r\n','\n').replace('\n','\r\n').encode())
        (out/'MTCP.CFG').write_text('PACKETINT 0x60\nHOSTNAME RELEASE-TEST\nIPADDR 10.0.2.15\nNETMASK 255.255.255.0\nGATEWAY 10.0.2.2\nMTU 1500\n')
        config = directory/'DOSBOX.CONF'
        config.write_text('[cpu]\ncputype=8086\ncycles=max\n[dosbox]\nmachine=hercules\nmemsize=1\n[serial]\nserial2=disabled\n[ne2000]\nne2000=true\nnicbase=300\nnicirq=3\nmacaddr=AC:DE:48:10:40:01\nbackend=slirp\n[ethernet, slirp]\nrestricted=false\ndisable_host_loopback=false\n')
        batch = ['@echo off','NE2K.COM 0x60 3 0x300 > PKT.LOG','set MTCPCFG=C:\\MTCP.CFG',
                 'AI4DOS.EXE AI4DOS.CFG release-delta > DOS.LOG', 'if errorlevel 1 goto failed',
                 'echo PASS > TEST.STA', 'goto finished', ':failed', 'echo FAIL > TEST.STA', ':finished']
        (out/'TEST.BAT').write_bytes(('\r\n'.join(batch)+'\r\n').encode())
        args = ['dosbox-x','-defaultconf','-conf',str(config),'-nogui','-silent','-fastlaunch','-time-limit','30']
        for command in (f'mount c "{out}"','c:','TEST.BAT','exit'):
            args += ['-c',command]
        with (directory/'emulator.log').open('wb') as log:
            proc = await asyncio.create_subprocess_exec(*args,stdout=log,stderr=log)
            await asyncio.wait_for(proc.wait(), 40)
        assert 'PASS' in (out/'TEST.STA').read_text()
        assert 'AI4DOS UI scripted chat completed.' in (out/'DOS.LOG').read_text()
        assert provider.calls==1
        assert hashlib.sha256((out/'AI4DOS.EXE').read_bytes()).hexdigest()==json.loads((ROOT/'release/inputs/dos-build.json').read_text())['sha256']['release/inputs/AI4DOS.EXE']
        print('DOS fresh ZIP: emulated 8086/Hercules, supplied config edited, one authenticated mock chat and clean application exit: PASS; external test driver, no physical XT test', flush=True)
    finally:
        if proc is not None and proc.returncode is None:
            proc.kill()
            await proc.wait()
        listener.close()
        await listener.wait_closed()
        await gateway.close()

async def docker(directory):
    out = directory/'docker'
    extract(ROOT/'dist/AI4DOS-Server-Docker.zip',out)
    subprocess.run(['docker','build','--pull=false','-t','ai4dos-release-sync:20261007',str(out)],check=True)
    config = out/'config.local/gateway.json'
    data = json.loads(config.read_text())
    data['devices'] = {'dos-pc':'synthetic-local-docker-key'}
    config.write_text(json.dumps(data))
    config.chmod(0o644)
    provider = out/'config.local/provider.cfg'
    provider.write_text('PROVIDER=mock\nMODEL=mock\nAPI_KEY=\nREASONING=none\n')
    provider.chmod(0o644)
    name = 'ai4dos-release-sync-20261007'
    try:
        subprocess.run(['docker','run','-d','--name',name,'--network','none','--user','10001:10001',
            '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true',
            '--mount',f'type=bind,src={config},dst=/config/gateway.json,readonly',
            '--mount',f'type=bind,src={provider},dst=/config/provider.cfg,readonly',
            'ai4dos-release-sync:20261007'],check=True,stdout=subprocess.DEVNULL)
        for i in range(30):
            test = subprocess.run(['docker','exec',name,'python','/app/tools/docker-healthcheck.py'],capture_output=True)
            if test.returncode==0:
                break
            await asyncio.sleep(0.5)
        else:
            raise AssertionError('Docker startup/healthcheck failed')
        state = json.loads(subprocess.check_output(['docker','inspect',name]))[0]
        assert state['Config']['User']=='10001:10001'
        assert state['HostConfig']['ReadonlyRootfs']
        assert state['HostConfig']['NetworkMode']=='none'
        assert all(not m['RW'] for m in state['Mounts'])
        code = 'import hashlib,json,pathlib; p=pathlib.Path("/app"); print(json.dumps({str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (p/"server/src/ai4dos").glob("*.py")}))'
        actual = json.loads(subprocess.check_output(['docker','exec',name,'python','-c',code]))
        for name_in_repo,digest in actual.items():
            assert digest==hashlib.sha256((ROOT/name_in_repo).read_bytes()).hexdigest()
        assert len(actual)==12
        print('Docker fresh ZIP: image built from ZIP; shipped manual configs, UID10001, read-only root and config mounts, healthcheck, exact current modules: PASS; network disabled; no Portainer UI redeploy', flush=True)
    finally:
        subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.run(['docker','image','rm','ai4dos-release-sync:20261007'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

async def main():
    with tempfile.TemporaryDirectory(prefix='AI4DOS runtime delta ') as folder:
        directory = Path(folder).resolve()
        await dos(directory)
        await docker(directory)

if __name__ == '__main__':
    asyncio.run(main())
