#!/bin/sh
set -eu
repo_dir=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
: "${DOSBOX_X:=dosbox-x}"
python3 - "$repo_dir" <<'PYBUILD'
from pathlib import Path
import sys
r=Path(sys.argv[1]);b=r/'client/build'
for name,obj in [('VTEST','vtest'),('UIE2E','uikeys'),('TSTEST','tstest'),('STRESS','uistress'),('RECON','uireconn'),('SYSTEM','systest')]:
    if name=='VTEST':
        link="system dos\noption stack=8192\nname build\\VTEST.EXE\nfile build\\vtest.obj,build\\ui.obj,build\\video.obj,build\\glyphs.obj,build\\editor.obj,build\\controls.obj,build\\l10n.obj,build\\transcr.obj,build\\chatfile.obj\n"
    elif name=='TSTEST':
        link="system dos\noption stack=8192\nname build\\TSTEST.EXE\nfile build\\tstest.obj,build\\ui.obj,build\\video.obj,build\\glyphs.obj,build\\editor.obj,build\\controls.obj,build\\l10n.obj,build\\transcr.obj,build\\chatfile.obj\n"
    elif name=='SYSTEM':
        link="system dos\noption stack=8192\nname build\\SYSTEM.EXE\nfile build\\systest.obj,build\\video.obj,build\\glyphs.obj,build\\editor.obj,build\\controls.obj,build\\l10n.obj,build\\transcr.obj,build\\chatfile.obj,build\\config.obj,build\\charset.obj,build\\protocol.obj,build\\sha256.obj\n"
    else:
        link=(r/'client/AI4DOS.LNK').read_text().replace('AI4DOS.EXE',name+'.EXE').replace('AI4DOS.MAP',name+'.MAP').replace('build\\ui.obj','build\\'+obj+'.obj')
    (b/(name+'.LNK')).write_text(link)
lines=['@echo off']
for obj,name in [('vtest','VTEST'),('uikeys','UIE2E'),('tstest','TSTEST'),('uistress','STRESS'),('uireconn','RECON'),('systest','SYSTEM')]:
    lines += [f'wcc -0 -ml -bt=dos -d0 -s -os -zq -i=include -fo=build\\{obj}.obj tests\\{obj}.c','if errorlevel 1 goto failed',f'wlink @build\\{name}.LNK','if errorlevel 1 goto failed']
lines+=['echo PASS > build\\UITBUILD.STA','goto finished',':failed','echo FAIL > build\\UITBUILD.STA',':finished']
(b/'UITBUILD.STA').unlink(missing_ok=True)
(b/'UITBUILD.BAT').write_bytes(('\r\n'.join(lines)+'\r\n').encode('ascii'))
PYBUILD
"$DOSBOX_X" -defaultconf -nogui -silent -fastlaunch -set 'cpu cycles=max' -time-limit 120 \
 -c "mount c \"$repo_dir/client\"" -c "mount d \"$repo_dir/client/build/watcom\"" \
 -c 'c:' -c 'set WATCOM=D:\' -c 'set PATH=D:\BINW;%PATH%' -c 'set INCLUDE=D:\H' \
 -c 'build\UITBUILD.BAT > build\UITBUILD.LOG' -c exit
grep -q PASS "$repo_dir/client/build/UITBUILD.STA"
