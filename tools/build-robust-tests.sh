#!/bin/sh
set -eu
repo_dir=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
: "${DOSBOX_X:=dosbox-x}"
python3 - "$repo_dir" <<'PY'
from pathlib import Path
import sys
r=Path(sys.argv[1]);b=r/'client/build'
s=(r/'client/AI4DOS.LNK').read_text().replace('AI4DOS.EXE','ROBUST.EXE').replace('AI4DOS.MAP','ROBUST.MAP').replace('build\\ui.obj','build\\robustui.obj')
(b/'ROBUST.LNK').write_text(s)
objs='ui video glyphs editor controls l10n transcr chatfile'.split()
(b/'INFO.LNK').write_text('system dos\noption stack=8192\nname build\\INFO.EXE\nfile build\\infotest.obj,'+','.join('build\\'+x+'.obj' for x in objs)+'\n')
lines=['@echo off','wcc -0 -ml -bt=dos -d0 -s -os -zq -fo=build\\screenrd.obj tests\\screenrd.c','if errorlevel 1 goto failed','wlink system dos name build\\DUMP.EXE file build\\screenrd.obj','if errorlevel 1 goto failed','wcc -0 -ml -bt=dos -d0 -s -os -zq -i=include -fo=build\\robustui.obj tests\\robustui.c','if errorlevel 1 goto failed','wlink @build\\ROBUST.LNK','if errorlevel 1 goto failed','wcc -0 -ml -bt=dos -d0 -s -os -zq -i=include -fo=build\\infotest.obj tests\\infotest.c','if errorlevel 1 goto failed','wlink @build\\INFO.LNK','if errorlevel 1 goto failed','echo PASS > build\\ROBUST.STA','goto finished',':failed','echo FAIL > build\\ROBUST.STA',':finished']
(b/'RBUILD.BAT').write_bytes(('\r\n'.join(lines)+'\r\n').encode('ascii'))
PY
"$DOSBOX_X" -defaultconf -nogui -silent -fastlaunch -set 'cpu cycles=max' -time-limit 120 \
 -c "mount c \"$repo_dir/client\"" -c "mount d \"$repo_dir/client/build/watcom\"" \
 -c 'c:' -c 'set WATCOM=D:\' -c 'set PATH=D:\BINW;%PATH%' -c 'set INCLUDE=D:\H' \
 -c 'build\RBUILD.BAT > build\RBUILD.LOG' -c exit
grep -q PASS "$repo_dir/client/build/ROBUST.STA"
