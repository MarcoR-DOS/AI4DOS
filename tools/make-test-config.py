#!/usr/bin/env python3
"""Generate a matched, ignored local test configuration without printing secrets."""
import json
import os
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
gateway = root / '.dev/gateway.local.json'
client = root / 'client/build/TEST.CFG'
if gateway.exists() or client.exists():
    raise SystemExit('Local config already exists; no files changed.')
gateway.parent.mkdir(exist_ok=True)
client.parent.mkdir(exist_ok=True)
secret = secrets.token_hex(32)
for path, contents in (
    (gateway, json.dumps({'host': '127.0.0.1', 'port': 1983,
                         'devices': {'test-device': secret},
                         'provider': 'mock', 'output_mode': 'dos'}, indent=2) + '\n'),
    (client, 'SERVER=127.0.0.1\nPORT=1983\nDEVICE=test-device\nSECRET=' + secret + '\n'),
):
    with os.fdopen(os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as file:
        file.write(contents)
print('Created matched local mock configs in .dev/ and client/build/.')
