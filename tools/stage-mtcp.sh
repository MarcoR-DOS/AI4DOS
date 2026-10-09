#!/bin/sh
set -eu
: "${MTCP_SOURCE:?Set MTCP_SOURCE to a read-only local upstream mTCP checkout}"
repo_dir=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
base=dbb161efb723da4a9eaadc7436c2110492370acd
actual=$(git --no-optional-locks -C "$MTCP_SOURCE" rev-parse HEAD)
test "$actual" = "$base"
stage="$repo_dir/client/build/mtcp"
test ! -e "$stage" || { printf '%s\n' 'Stage already exists; remove only the AI4DOS staged copy to restage.' >&2; exit 1; }
mkdir -p "$stage"
git --no-optional-locks -C "$MTCP_SOURCE" archive "$base" LICENSE src/TCPINC src/TCPLIB | tar -xf - -C "$stage"
patch -s -d "$stage" -p1 < "$repo_dir/tools/mtcp-cleanup.patch"
# Mark the modified GPL-covered files while retaining all upstream notices.
python3 - "$stage" <<'PYNOTICE'
from pathlib import Path
import sys
stage = Path(sys.argv[1])
notice = (b"/* AI4DOS build modifications, 2026-10-06: cleanup/pool lifetime and\n"
          b"   Watcom far-model heap check. See tools/mtcp-cleanup.patch. */\n")
for name in ("PACKET.CPP", "TCP.CPP", "TCPSOCKM.CPP", "UTILS.CPP"):
    path = stage / "src/TCPLIB" / name
    path.write_bytes(notice + path.read_bytes())
PYNOTICE
printf '%s\n' "$base" > "$stage/SOURCE-COMMIT"
printf '%s\n' 'mTCP staged only in AI4DOS client/build/mtcp.'
