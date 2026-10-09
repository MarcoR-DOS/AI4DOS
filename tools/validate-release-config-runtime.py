"""Offline Docker/Portainer release delta: real config key, no provider requests."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'ai4dos-config-delta:20261007'

def main():
    env = {k:v for k,v in os.environ.items() if not k.endswith('API_KEY') and not k.startswith('AI4DOS_')}
    def run(args, cwd, capture=True):
        return subprocess.run(args, cwd=cwd, env=env, check=True, capture_output=capture, text=True).stdout
    with tempfile.TemporaryDirectory(prefix='ai4dos-config-delta-') as folder:
        out = Path(folder)
        with zipfile.ZipFile(ROOT/'dist/AI4DOS-Server-Docker.zip') as z:
            z.extractall(out)
            for entry in z.infolist():
                (out/entry.filename).chmod(entry.external_attr >> 16 & 0o777)
        gateway = out/'config.local/gateway.json'
        data = json.loads(gateway.read_text())
        data['devices'] = {'dos-pc':'synthetic-local-device-key'}
        gateway.write_text(json.dumps(data))
        provider = out/'config.local/provider.cfg'
        provider.write_text(provider.read_text().replace('API_KEY=\n','API_KEY=SYNTHETIC_OFFLINE_DELTA_KEY\n'))
        env.update(AI4DOS_GATEWAY_CONFIG=str(gateway), AI4DOS_PROVIDER_CONFIG=str(provider))
        assert not (out/'.env').exists()
        run(['docker','build','--pull=false','-t',IMAGE,'.'],out,False)
        try:
            for stack, project in (('docker-compose.yml','ai4dos-config-delta-compose'),('portainer-stack.yml','ai4dos-config-delta-portainer')):
                # Only isolation and image tag differ from shipped services. No host port or network access.
                override = out/'test-isolation.yml'
                override.write_text('services:\n  gateway:\n    image: '+IMAGE+'\n    network_mode: none\n    ports: !reset []\n    restart: "no"\n')
                command = ['docker','compose','-p',project,'-f',stack,'-f',str(override)]
                rendered = json.loads(run(command+['config','--format','json'],out))
                assert not rendered['services']['gateway'].get('environment')
                try:
                    run(command+['up','-d','--no-build','--pull','never'],out)
                    cid = run(command+['ps','-q'],out).strip()
                    for _ in range(40):
                        check = subprocess.run(['docker','exec',cid,'python','/app/tools/docker-healthcheck.py'],cwd=out,env=env,capture_output=True)
                        if check.returncode == 0:
                            break
                        time.sleep(0.5)
                    else:
                        raise AssertionError('Gateway healthcheck did not succeed')
                    code = ('import os,asyncio; from ai4dos.config import Settings,build_provider; '
                            'assert not any(k.endswith("API_KEY") for k in os.environ); '
                            's=Settings.load("/config/gateway.json"); '
                            'assert s.api_key=="SYNTHETIC_OFFLINE_DELTA_KEY"; '
                            'p=build_provider(s); asyncio.run(p.close()); print("config-key construction PASS")')
                    assert 'PASS' in run(['docker','exec',cid,'python','-c',code],out)
                    state=json.loads(run(['docker','inspect',cid],out))[0]
                    assert state['HostConfig']['NetworkMode']=='none'
                    assert state['Config']['User']=='10001:10001'
                    assert state['HostConfig']['ReadonlyRootfs']
                    assert all(not m['RW'] for m in state['Mounts'])
                    logs=run(command+['logs','--no-color'],out)
                    assert 'SYNTHETIC_OFFLINE_DELTA_KEY' not in logs
                    assert 'AI4DOS gateway ready on port 1983' in logs
                    print(stack+': fresh ZIP image, config-only API key, no .env/API-key environment, network disabled, real startup + healthcheck: PASS')
                finally:
                    run(command+['down','--remove-orphans'],out)
        finally:
            run(['docker','image','rm',IMAGE],out)

if __name__ == '__main__':
    main()
