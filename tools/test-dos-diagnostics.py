#!/usr/bin/env python3
"""Targeted DOS/8086 diagnostics and clean F10-after-loss checks; offline mocks.
No image captures. Console assertions use the existing BIOS text-cell reader.
Use --baseline before product changes to reproduce the delayed stderr message.
"""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server/src'))
from ai4dos.config import Settings
from ai4dos.server import Gateway
from ai4dos.provider import MockProvider
spec=importlib.util.spec_from_file_location('matrix',ROOT/'tools/test-dos-robustness.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
async def main():
    baseline='--baseline' in sys.argv
    m.RESULT_FILE=m.B/('DIAG-BEFORE.json' if baseline else 'DIAG-AFTER.json')
    class Recorded(Gateway):
        connections=0;replies=0;resumes=0
        async def handle(self,reader,writer):
            self.connections+=1
            await super().handle(reader,writer)
        async def respond(self,writer,session,message):
            self.replies+=1
            await super().respond(writer,session,message)
        async def write(self,writer,line):
            if line=='OK RESUME':self.resumes+=1
            await super().write(writer,line)
    # Idle timeout changed only on this ephemeral test object.
    g=Recorded(Settings(port=0,idle_timeout=0.7,devices={'test-device':'local-test-key'}),MockProvider())
    listener=await g.start();port=listener.sockets[0].getsockname()[1]
    cfg=m.BASE.replace('PORT=9',f'PORT={port}')
    try:
        if not baseline:
            for name,testcfg,ip,expect in [
                ('null IP',cfg,m.IP.replace('10.0.2.15','0.0.0.0'),'No valid IP address assigned.'),
                ('invalid SERVER',cfg.replace('10.0.2.2','999.1.1.1'),m.IP,'Invalid server address.'),
                ('off-subnet without gateway',cfg.replace('10.0.2.2','10.0.3.2'),m.IP.replace('GATEWAY 10.0.2.2\n',''),'Network gateway not configured.'),
            ]:
                before=g.connections
                await asyncio.to_thread(m.run,name,cfg=testcfg,ip=ip,driver=True,expect=expect)
                assert g.connections==before,(name,'unexpected gateway connection')
                item=m.results[-1]
                assert 'Gateway unreachable.' not in item['transcript']
                assert not item['console'].strip(),(name,item['console'])
            for name,ip in [
                ('valid static IP',m.IP),
                ('same subnet without gateway',m.IP.replace('GATEWAY 10.0.2.2\n','')),
                ('valid DHCP lease configuration',m.IP+f'TIMESTAMP ( {int(time.time())} )\nLEASE_TIME 86400\n'),
            ]:
                before=g.replies
                await asyncio.to_thread(m.run,name,cfg=cfg,ip=ip,driver=True,expect='Connected. You can start chatting.',mode='chat')
                assert g.replies==before+1
                assert m.results[-1]['state']=='PASS'
                assert not m.results[-1]['console'].strip(),(name,m.results[-1]['console'])
            await asyncio.to_thread(m.run,'packet driver absent',cfg=cfg,expect='Packet driver not found')
            assert not m.results[-1]['console'].strip()
        before=g.replies
        await asyncio.to_thread(m.run,'reply / idle loss / F10',cfg=cfg,driver=True,expect='Connection lost.',mode='idlequit',machine='vgaonly')
        assert g.replies==before+1 and g.resumes==0
        console=m.results[-1]['console']
        if baseline:
            assert 'Network disconnected while waiting for input.' in console,console
            print('BASELINE REPRODUCED: delayed stderr after clean F10; chat already contained Connection lost.',flush=True)
        else:
            assert not console.strip(),console
            assert m.results[-1]['state']=='PASS'
            print('F10 after detected idle loss PASS: actual reply, UI loss, exit 0, no console diagnosis.',flush=True)
        print('Targeted DOS diagnostics PASS:',len(m.results),'cases; DHCP lease fixture is synthetic, not a DHCP exchange.',flush=True)
    finally:
        listener.close();await listener.wait_closed();await g.close()
        (m.B/'QA.CFG').unlink(missing_ok=True)
if __name__=='__main__':asyncio.run(main())
