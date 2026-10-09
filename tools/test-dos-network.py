#!/usr/bin/env python3
"""Run the actual DOS executable against an ephemeral loopback mock gateway."""
import asyncio
import hashlib
import os
from pathlib import Path
import secrets
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server/src'))
from ai4dos.config import Settings
from ai4dos.provider import MockProvider
from ai4dos.server import Gateway


async def main():
    build = ROOT / 'client/build'
    driver = Path(os.environ['NE2K_DRIVER'])
    if hashlib.sha256(driver.read_bytes()).hexdigest() != 'f95b36199a47bf7e6eb03cb9474e97d50cb9c23de08996a036bb525599e0b9f2':
        raise ValueError('Unexpected test driver hash; see third_party/PACKET-DRIVER-TEST.md')
    if driver.resolve() != (build / 'NE2K.COM').resolve():
        shutil.copyfile(driver, build / 'NE2K.COM')
    (build / 'MTCP.CFG').write_text('PACKETINT 0x60\nHOSTNAME AI4DOS-TEST\nIPADDR 10.0.2.15\nNETMASK 255.255.255.0\nGATEWAY 10.0.2.2\nMTU 1500\n')
    conf = build / 'NETWORK.CONF'
    conf.write_text('[cpu]\ncputype=8086\ncycles=max\n[dosbox]\nmachine=hercules\nmemsize=1\n[serial]\nserial2=disabled\n[ne2000]\nne2000=true\nnicbase=300\nnicirq=3\nmacaddr=AC:DE:48:10:40:01\nbackend=slirp\n[ethernet, slirp]\nrestricted=false\ndisable_host_loopback=false\n')
    secret = secrets.token_hex(32)
    class RecordedMock(MockProvider):
        calls = 0
        async def stream(self, messages):
            assert all(not m.text.startswith("System:") for m in messages), "Local system event entered model context"
            self.calls += 1
            if self.calls>1 and self.calls%2==1:
                assert len(messages) == 1, 'F2 did not create a fresh session'
            assert messages[-1].text == ('hello-again' if self.calls>1 and self.calls%2==1 else 'hello-dos')
            async for delta in super().stream(messages):
                yield delta
    provider = RecordedMock()
    class RecordedGateway(Gateway):
        byes = 0
        auth_failures = 0
        session_count = 0
        async def write(self, writer, line):
            if line.startswith('SESSION '): self.session_count += 1
            if line == 'OK BYE': self.byes += 1
            if line.startswith('ERROR AUTH_FAILED '): self.auth_failures += 1
            await super().write(writer, line)
    gateway = RecordedGateway(Settings(port=0, devices={'test-device': secret}), provider)
    server = await gateway.start()
    port = server.sockets[0].getsockname()[1]
    cfg = build / 'DOS.CFG'
    proc = None
    try:
        for bad, interactive, language in ((False, False, None), (True, False, None), (False, True, None), (False, True, "en"), (False, True, "de"), (False, True, "unknown")):
            (build/"STATUS.LOG").unlink(missing_ok=True)
            previous_calls=provider.calls;previous_byes=gateway.byes;previous_sessions=gateway.session_count
            if interactive and not (build / "UIE2E.EXE").exists():
                print("Interactive keyboard test skipped: build UIE2E.EXE first")
                continue
            cfg.write_text(f'SERVER=10.0.2.2\nPORT={port}\nDEVICE=test-device\nSECRET={secrets.token_hex(32) if bad else secret}\n')
            if language is not None:
                with cfg.open("a") as f:f.write(f"LANGUAGE={language}\nCODEPAGE=850\n")
            cfg.chmod(0o600)
            log = 'UI.LOG' if interactive else 'BAD.LOG' if bad else 'DOS.LOG'
            state_name = 'UI.STA' if interactive else 'BAD.STA' if bad else 'DOS.STA'
            state = build / state_name
            state.unlink(missing_ok=True)
            executable = 'UIE2E.EXE' if interactive or bad else 'AI4DOS.EXE'
            message_arg = '' if interactive else ' hello-dos'
            batch = ['@echo off', 'cd build', 'NE2K.COM 0x60 3 0x300 > PKT.LOG', 'set MTCPCFG=C:\\build\\MTCP.CFG', f'{executable} DOS.CFG{message_arg} > {log}', 'if errorlevel 1 goto failed', f'echo PASS > {state_name}', 'goto finished', ':failed', f'echo FAIL > {state_name}', ':finished']
            (build / 'RUN.BAT').write_bytes(('\r\n'.join(batch)+'\r\n').encode('ascii'))
            commands = [f'mount c "{ROOT / "client"}"', 'c:', 'build\\RUN.BAT', 'exit']
            args = [os.environ.get('DOSBOX_X', 'dosbox-x'), '-defaultconf', '-conf', str(conf), '-nogui', '-silent', '-fastlaunch', '-time-limit', '30']
            for command in commands:
                args += ['-c', command]
            with (build / ('EMU-BAD.LOG' if bad else 'EMU-DOS.LOG')).open('wb') as emulator_log:
                proc = await asyncio.create_subprocess_exec(*args, stdout=emulator_log, stderr=emulator_log)
                await asyncio.wait_for(proc.wait(), 40)
            text = (build / log).read_text()
            if bad:
                assert 'FAIL' in state.read_text(), text
                # stderr appears on the emulator screen, never in redirected stdout.
                assert provider.calls == previous_calls, 'Bad authentication reached provider'
                statuses=(build/'STATUS.LOG').read_text().splitlines()
                assert statuses[0]=='CONNECTING' and statuses[-1]=='ERROR',statuses
                assert gateway.auth_failures == 1, 'Expected authentication failure was not observed'
            else:
                assert 'PASS' in state.read_text(), text
                if not interactive:
                    assert 'AI4DOS UI scripted chat completed.' in text, text
                assert provider.calls == previous_calls+(2 if interactive else 1)
                assert gateway.byes == previous_byes+1, 'QUIT/OK BYE was not observed'
            if interactive:
                statuses=(build/'STATUS.LOG').read_text().splitlines()
                assert statuses[0]=='CONNECTING' and statuses[-1]=='ONLINE',statuses
                assert statuses.count('TX/RX')==2 and set(statuses)<={'CONNECTING','ONLINE','TX/RX'},statuses
                for j,status in enumerate(statuses):
                    if status=='TX/RX':assert statuses[j+1]=='ONLINE',statuses
                (build/('STATUS-'+(language or 'default')+'.LOG')).write_text('\n'.join(statuses))
                print('DOS language/status PASS:',language or 'default English')
                assert gateway.session_count == previous_sessions+2, 'Expected two sessions in interactive client'
            await asyncio.sleep(0.05)
            assert not gateway.active, 'Connection was not released'
        print('DOS 8086 mTCP E2E PASS; bad-auth PASS; connections released; interactive help/info/save-cancel/F2/new/exit-confirmation covered when UIE2E.EXE exists')
    finally:
        if proc is not None and proc.returncode is None:
            proc.kill()
            await proc.wait()
        cfg.unlink(missing_ok=True)
        server.close()
        await server.wait_closed()
        await gateway.close()


if __name__ == '__main__':
    asyncio.run(main())
