#!/bin/sh
set -eu
: "${WATCOM_ROOT:?Set WATCOM_ROOT to an existing Open Watcom DOS toolchain}"
repo_dir=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
: "${DOSBOX_X:=dosbox-x}"
for tool in wcc wpp wasm wlink; do
    test -f "$WATCOM_ROOT/binw/$tool.exe"
done
for directory in h lib286; do test -d "$WATCOM_ROOT/$directory"; done
test "$(cat "$repo_dir/client/build/mtcp/SOURCE-COMMIT")" = dbb161efb723da4a9eaadc7436c2110492370acd
python3 "$repo_dir/tools/verify-watcom.py" "$WATCOM_ROOT"
# Compiler copy isolates all possible compiler writes from the reference tree.
mkdir -p "$repo_dir/client/build/watcom"
if [ "$(CDPATH= cd -- "$WATCOM_ROOT" && pwd -P)" != "$(CDPATH= cd -- "$repo_dir/client/build/watcom" && pwd -P)" ]; then
    cp -R "$WATCOM_ROOT/binw" "$WATCOM_ROOT/h" "$WATCOM_ROOT/lib286" "$repo_dir/client/build/watcom/"
fi
# DOS compiler programs are invoked by COMMAND.COM; long C++ options live in WPP.
python3 - "$repo_dir" <<'PYBUILD'
from pathlib import Path
import sys
root = Path(sys.argv[1])
commands = ["@echo off", "set WPP=-0 -ml -bt=dos -d0 -s -os -oh -ok -oa -ei -ob -ol+ -oi+ -zq -zp2 -zpw -we -fi=include\\mtcpcfg.h -i=include -i=E:\\TCPINC"]
for name in ("main", "charset", "config", "protocol", "sha256", "network", "video", "glyphs", "editor", "ui", "controls", "l10n", "transcr", "chatfile"):
    commands.append(f"wcc -0 -ml -bt=dos -d0 -s -os -zq -i=include -fo=build\\{name}.obj src\\{name}.c")
commands.append("wpp src\\mtcpadpt.cpp -fo=build\\mtcpadpt.obj")
for name in ("packet", "arp", "eth", "ip", "tcp", "tcpsockm", "utils", "timer"):
    commands.append(f"wpp E:\\TCPLIB\\{name}.cpp -fo=build\\{name}.obj")
commands += ["wasm -0 -ml -zq -fo=build\\ipasm.obj E:\\TCPLIB\\ipasm.asm", "wlink @AI4DOS.LNK", "wcc -0 -ml -bt=dos -d0 -s -os -zq -i=include -fo=build\\coretest.obj tests\\coretest.c", "wlink system dos option stack=8192 name build\\CORETEST.EXE file build\\coretest.obj,build\\protocol.obj,build\\sha256.obj", "wcc -0 -ml -bt=dos -d0 -s -os -zq -i=include -fo=build\\chartest.obj tests\\chartest.c", "wlink system dos option stack=8192 name build\\ENCODING.EXE file build\\chartest.obj,build\\charset.obj"]
checked = commands[:2] + ["echo AI4DOS build > build\\BUILD.LOG"]
for command in commands[2:]:
    checked += [command + " >> build\\BUILD.LOG", "if errorlevel 1 goto failed"]
checked += ["echo PASS > build\\BUILD.STA", "goto finished", ":failed", "echo FAIL > build\\BUILD.STA", ":finished"]
commands = checked
for name in ("AI4DOS.EXE", "CORETEST.EXE", "BUILD.STA", "CORE.LOG", "ENCODING.EXE", "ENCODING.LOG"):
    (root / "client/build" / name).unlink(missing_ok=True)
(root / "client/build/BUILD.BAT").write_bytes(("\r\n".join(commands)+"\r\n").encode("ascii"))
PYBUILD
"$DOSBOX_X" -defaultconf -nogui -silent -fastlaunch -set 'cpu cycles=max' -time-limit 240 \
 -c "mount c \"$repo_dir/client\"" -c "mount d \"$repo_dir/client/build/watcom\"" \
 -c "mount e \"$repo_dir/client/build/mtcp/src\"" \
 -c 'c:' -c 'set WATCOM=D:\' -c 'set PATH=D:\BINW;%PATH%' -c 'set INCLUDE=D:\H' \
 -c 'build\BUILD.BAT' \
 -c 'exit'
grep -q PASS "$repo_dir/client/build/BUILD.STA"
"$DOSBOX_X" -defaultconf -nogui -silent -fastlaunch \
 -machine hercules -set 'cpu cputype=8086' -set 'cpu cycles=max' -time-limit 30 \
 -c "mount c \"$repo_dir/client\"" -c 'c:' \
 -c 'build\CORETEST.EXE > build\CORE.LOG' -c 'build\ENCODING.EXE > build\ENCODING.LOG' -c 'exit'
test -f "$repo_dir/client/build/AI4DOS.EXE"
grep -q 'AI4DOS CORE PASS' "$repo_dir/client/build/CORE.LOG"

grep -q "AI4DOS ENCODING PASS" "$repo_dir/client/build/ENCODING.LOG"
