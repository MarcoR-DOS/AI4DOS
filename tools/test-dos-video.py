from pathlib import Path
import subprocess,os
r=Path(__file__).resolve().parents[1];b=r/'client/build'
assert (b/'VTEST.EXE').exists()
for machine,arg in [('hercules','MDA'),('cga','CGA'),('ega','EGA'),('vgaonly','VGA')]:
 (b/'SCREEN.BIN').unlink(missing_ok=True)
 (b/'VFAIL.LOG').unlink(missing_ok=True)
 log=arg+'.LOG';state=arg+'.STA';(b/state).unlink(missing_ok=True)
 lines=['@echo off',fr'build\VTEST.EXE {arg} > build\{log}','if errorlevel 1 goto failed',fr'echo PASS > build\{state}','goto finished',':failed',fr'echo FAIL > build\{state}',':finished']
 (b/'VRUN.BAT').write_bytes(('\r\n'.join(lines)+'\r\n').encode('ascii'))
 args=[os.environ.get('DOSBOX_X','dosbox-x'),'-defaultconf','-machine',machine,'-nogui','-silent','-fastlaunch','-set','cpu cputype=8086','-set','cpu cycles=max','-time-limit','30']
 for c in [f'mount c "{r / "client"}"','c:',r'build\VRUN.BAT','exit']:args+=['-c',c]
 with (b/f'video-{arg}.log').open('wb') as output:subprocess.run(args,stdout=output,stderr=output,timeout=40,check=True)
 if (b/'VFAIL.LOG').exists():print((b/'VFAIL.LOG').read_text(),flush=True)
 print(arg,(b/state).read_text().strip(),(b/log).read_text().strip(),flush=True)
 assert (b/state).read_text().strip()=='PASS',arg
 if (b/'SCREEN.BIN').exists():(b/(arg+'.BIN')).write_bytes((b/'SCREEN.BIN').read_bytes())
