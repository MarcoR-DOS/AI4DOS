#!/bin/sh
set -eu
repo_dir=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
exe=${1:-$repo_dir/client/build/AI4DOS.EXE}
: "${GOBJDUMP:=gobjdump}"
identity=$("$GOBJDUMP" -f "$exe")
printf '%s\n' "$identity" | grep -q 'file format msdos'
printf '%s\n' "$identity" | grep -q 'architecture: i8086'
if strings -a "$exe" | grep -Eiq 'DOS/4G|DOS32|protected.mode|PMODE|CAUSEWAY|extender|OS/2 executable'; then
    printf '%s\n' 'Unexpected extender/protected-mode marker' >&2
    exit 1
fi
printf '%s\n' "$identity" 'No DOS-extender marker found; instruction target also requires the -0 build and 8086 runtime tests.'
