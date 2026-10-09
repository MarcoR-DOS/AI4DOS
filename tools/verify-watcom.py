#!/usr/bin/env python3
"""Verify the tested DOS compiler, headers and runtime without modifying them."""
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
manifest = json.loads((Path(__file__).resolve().parents[1] /
                       'third_party/watcom-toolchain.json').read_text())
for name, expected in manifest['trees'].items():
    digest = hashlib.sha256()
    folder = root / name
    for file in sorted(folder.rglob('*')):
        if file.is_file():
            digest.update(file.relative_to(folder).as_posix().encode('utf-8') +
                          b'\0' + hashlib.sha256(file.read_bytes()).digest())
    if digest.hexdigest() != expected:
        raise SystemExit('Untested Open Watcom tree: ' + name +
                         '; see third_party/WATCOM.md')
print('Tested Open Watcom DOS toolchain verified.')
