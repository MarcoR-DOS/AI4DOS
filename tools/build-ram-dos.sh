#!/bin/sh
# Requires a previously successful ordinary build; preserves its EXE and objects.
set -eu
repo_dir=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
: "${DOSBOX_X:=dosbox-x}"
test -f "$repo_dir/client/build/AI4DOS.EXE"
test -f "$repo_dir/client/build/watcom/binw/wcc.exe"
python3 - "$repo_dir" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1]); b=root/'client/build'
cmds=[r'wcc -0 -ml -bt=dos -d0 -s -os -zq -dAI4DOS_RAM_DIAG -i=include -fo=build\rammain.obj src\main.c',r'wcc -0 -ml -bt=dos -d0 -s -os -zq -dAI4DOS_RAM_DIAG -i=include -fo=build\ramdiag.obj src\ramdiag.c',r'wpp src\mtcpadpt.cpp -fo=build\ramadpt.obj',r'wlink @RAMDIAG.LNK']
lines=['@echo off',r'set WPP=-0 -ml -bt=dos -d0 -s -os -oh -ok -oa -ei -ob -ol+ -oi+ -zq -zp2 -zpw -we -dAI4DOS_RAM_DIAG -fi=include\mtcpcfg.h -i=include -i=E:\TCPINC',r'echo RAM diagnostic build > build\RAMBUILD.LOG']
for c in cmds: lines += [c+r' >> build\RAMBUILD.LOG','if errorlevel 1 goto failed']
lines += [r'echo PASS > build\RAMBUILD.STA','goto finished',':failed',r'echo FAIL > build\RAMBUILD.STA',':finished']
for n in ['A4RAM.EXE','RAMBUILD.STA']: (b/n).unlink(missing_ok=True)
(b/'RAMBUILD.BAT').write_bytes(('\r\n'.join(lines)+'\r\n').encode('ascii'))
PY
"$DOSBOX_X" -defaultconf -nogui -silent -fastlaunch -set 'cpu cycles=max' -time-limit 120 \
 -c "mount c \"$repo_dir/client\"" -c "mount d \"$repo_dir/client/build/watcom\"" \
 -c "mount e \"$repo_dir/client/build/mtcp/src\"" -c 'c:' -c 'set WATCOM=D:\' \
 -c 'set PATH=D:\BINW;%PATH%' -c 'set INCLUDE=D:\H' -c 'build\RAMBUILD.BAT' -c exit
grep -q PASS "$repo_dir/client/build/RAMBUILD.STA"
test -f "$repo_dir/client/build/A4RAM.EXE"
