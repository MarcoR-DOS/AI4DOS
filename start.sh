#!/bin/sh
# Run from the project directory, including when launched elsewhere.
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
    echo "Python environment is missing. Run the setup commands from the AI4DOS installation guide first." >&2
    exit 1
fi
.venv/bin/python -c 'import httpx, openai' >/dev/null 2>&1 || {
    echo "Gateway dependencies are missing. Run the dependency setup commands from the AI4DOS installation guide." >&2
    exit 1
}
PYTHONPATH="$PWD/server/src" exec .venv/bin/python -m ai4dos.server "$@"
