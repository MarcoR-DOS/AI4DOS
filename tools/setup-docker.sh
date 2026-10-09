#!/bin/sh
# One-time config preparation using the same helper, without host Python.
set -eu
cd "$(dirname "$0")/.."
docker compose build gateway
# Release ZIPs already contain editable configs. Keep user files untouched.
if [ -f config.local/gateway.json ] && [ -f config.local/provider.cfg ]; then
    echo "Config files already present. Edit config.local/gateway.json and config.local/provider.cfg before starting."
    exit 0
fi
docker run --rm --network none --read-only --cap-drop ALL \
    --security-opt no-new-privileges:true --user "$(id -u):$(id -g)" \
    --mount "type=bind,src=$PWD,dst=/setup" --entrypoint python \
    ai4dos-gateway:beta /setup/tools/setup-local.py --root /setup --docker "$@"
