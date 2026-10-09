#!/usr/bin/env python3
"""Offline production UI/main scenarios on an emulated 8086; no network."""
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
build = root / "client/build"
for executable, marker in (("SYSTEM", "AI4DOS SYSTEM PASS"),
                           ("TSTEST", "AI4DOS TRANSCRIPT SAVE SCROLL STRESS PASS"),
                           ("VTEST", "AI4DOS VIDEO")):
    log_name = executable[:6] + "DT.LOG"
    log = build / log_name
    log.unlink(missing_ok=True)
    (build / "VFAIL.LOG").unlink(missing_ok=True)
    commands = [f'mount c "{root / "client"}"', "c:"]
    if executable == "VTEST":
        commands += [f"build\\VTEST.EXE MDA > build\\{log_name}"]
    else:
        commands += ["cd build", f"{executable}.EXE > {log_name}"]
    args = [os.environ.get("DOSBOX_X", "dosbox-x"), "-defaultconf", "-nogui",
            "-silent", "-fastlaunch", "-machine", "hercules", "-set",
            "cpu cputype=8086", "-set", "cpu cycles=max", "-time-limit", "45"]
    for command in commands + ["exit"]:
        args += ["-c", command]
    with (build / (executable + "-EMULATOR.LOG")).open("wb") as output:
        subprocess.run(args, stdout=output, stderr=output, timeout=55, check=True)
    text = log.read_text(encoding="cp850")
    assert marker in text and "FAIL" not in text, text
    assert not (build / "VFAIL.LOG").exists(), "Video assertion failed"
    print(executable + " DOS/8086 PASS")
