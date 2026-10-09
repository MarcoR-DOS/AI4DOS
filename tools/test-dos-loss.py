#!/usr/bin/env python3
"""DOS/8086 TCP stream drop and confirmed mock-gateway idle close + RESUME.
Short timeout is confined to this ephemeral mock; production settings unchanged.
"""
import asyncio, importlib.util, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server/src'))
from ai4dos.config import Settings
from ai4dos.server import Gateway
from ai4dos.provider import MockProvider
spec=importlib.util.spec_from_file_location('matrix',ROOT/'tools/test-dos-robustness.py')
matrix=importlib.util.module_from_spec(spec);spec.loader.exec_module(matrix)
async def main():
    matrix.results=[]
    matrix.RESULT_FILE=matrix.B/'LOSS-RESULTS.json'
    for mode in ['drop','idle']:
        class Recorded(Gateway):
            resumes=0;drops=0;replies=0
            async def write(self,writer,line):
                if line=='OK RESUME':self.resumes+=1
                await super().write(writer,line)
            async def respond(self,writer,session,message):
                if message=='drop':
                    self.drops+=1
                    await self.write(writer,'BEGIN Mock')
                    await self.write(writer,'DATA partial')
                    writer.close()
                    return
                self.replies+=1
                await super().respond(writer,session,message)
        g=Recorded(Settings(port=0,idle_timeout=0.7 if mode=='idle' else 300,devices={'test-device':'local-test-key'}),MockProvider())
        server=await g.start();port=server.sockets[0].getsockname()[1]
        try:
            await asyncio.to_thread(matrix.run,mode+' / reconnect / resume',cfg=matrix.BASE.replace('PORT=9',f'PORT={port}'),driver=True,expect='Connection lost.',mode=mode)
            assert g.resumes==1 and g.replies==1,(mode,g.resumes,g.replies,g.drops)
            assert g.drops==(1 if mode=='drop' else 0)
            text=(matrix.B/'QA.TXT').read_text()
            assert 'Connection restored.' in text and 'after' in text
            assert 'Connection closed due to inactivity.' not in text
            print(mode,'PASS: actual TCP close, UI ERROR, /reconnect, authenticated RESUME, mock reply, controlled exit',flush=True)
        finally:
            server.close();await server.wait_closed();await g.close()
    (matrix.B/'LOSS-RESULTS.json').write_text(__import__('json').dumps(matrix.results,indent=2))
    (matrix.B/'QA.CFG').unlink(missing_ok=True)
if __name__=='__main__':asyncio.run(main())
