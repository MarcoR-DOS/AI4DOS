# Building and development checks

[Developer index](README.md) · [Release process](release-process.md)

## DOS client from a clean checkout

The repository uses shell wrappers that generate DOS batch files; there is no
additional Make/CMake build layer. The existing route needs a POSIX host, Python
3.9+, Git, tar, patch, DOSBox-X, GNU binutils for executable inspection, and the
externally supplied Open Watcom DOS tree. These wrappers are not native Windows
build instructions; Windows has a gateway starter, not an equivalent DOS wrapper.

The tested toolchain is **Open Watcom 2.0 beta, build 2026-09-27**; WLINK reports
`Sep 27 2026 05:43:39 (32-bit)`. Required inputs are `binw/wcc.exe`, `wpp.exe`,
`wasm.exe`, `wlink.exe`, `h/` and `lib286/`. The verifier checks the three trees
against [watcom-toolchain.json](../../third_party/watcom-toolchain.json).
A newer rolling build is not a proven substitute. The immutable upstream installer
mapping is still open; see [Watcom provenance](../../third_party/WATCOM.md).

The following paths are placeholders for external, locally supplied dependencies:

```sh
git clone https://github.com/mbbrutman/mTCP /path/to/mTCP
git -C /path/to/mTCP checkout --detach dbb161efb723da4a9eaadc7436c2110492370acd
MTCP_SOURCE=/path/to/mTCP sh tools/stage-mtcp.sh
WATCOM_ROOT=/path/to/watcom DOSBOX_X=dosbox-x sh tools/build-dos.sh
GOBJDUMP=gobjdump sh tools/verify-dos.sh
```

[stage-mtcp.sh](../../tools/stage-mtcp.sh) archives the pinned commit, applies
[mtcp-cleanup.patch](../../tools/mtcp-cleanup.patch), retains notices and marks
modified dependency files. It refuses an existing staged tree. For restaging,
remove only the generated `client/build/mtcp/` copy after checking that it contains
no work to preserve; do not change the reference mTCP checkout.

[build-dos.sh](../../tools/build-dos.sh) checks the pin and Watcom fingerprints,
copies the compiler tree into `client/build/watcom/`, and generates `BUILD.BAT`.
DOSBox mounts C=client, D=compiler copy, E=staged mTCP/src. Compiler execution uses
an emulated modern CPU; application compilation explicitly uses `-0` for 8086.

C flags are `-0 -ml -bt=dos -d0 -s -os -zq -i=include`. C++ uses the same target
and Large Model plus the optimization/alignment settings in the wrapper; its long
options live in `WPP` because of DOS command-line length. Assembly uses
`wasm -0 -ml -zq`. [AI4DOS.LNK](../../client/AI4DOS.LNK) selects `system dos` and
an 8192-byte stack. The inspected build links the 16-bit `lib286/dos/clibl.lib`
runtime; the directory name does not change the target to 286. No `lib386/`
runtime or DOS extender is included.

Outputs are `client/build/AI4DOS.EXE`, `AI4DOS.MAP`, `BUILD.LOG` and `BUILD.STA`.
The wrapper also builds and runs core/encoding tests under an 8086 DOSBox CPU;
their executables and logs are build evidence, not package inputs. `verify-dos.sh`
checks MZ/i8086 identity and extender markers. None of these alone proves every
runtime instruction or physical XT behavior.

## Host client checks

```sh
sh tools/build-native.sh
```

[build-native.sh](../../tools/build-native.sh) uses `cc -std=c89 -Wall -Wextra
-Werror` for the native transport client and core, UI, transcript, network,
charset and system-message checks. The host transport in
[native_transport.c](../../tests/native_transport.c) replaces mTCP. Host checks
exercise logic without proving DOS memory layout, NIC/IRQ behavior or BIOS output.
Additional DOS UI/video/network tooling is in `tools/build-ui-tests.sh`,
`tools/test-dos-ui-delta.py`, `tools/test-dos-video.py` and
`tools/test-dos-network.py`; consult those scripts for their environment-specific
fixtures. DOS emulator validation requires a suitable external Packet Driver
and does not establish physical XT behavior.

## Python gateway: source execution, no native binary build

Python 3.9+ is the repository's stated floor. Direct dependency ranges live in
[requirements.txt](../../server/requirements.txt); the tested transitive versions
and Python/platform markers live in
[requirements-lock.txt](../../server/requirements-lock.txt). Do not replace a
locked install with an unreviewed dependency upgrade.

On the POSIX gateway route (macOS/Linux):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r server/requirements-lock.txt
.venv/bin/python -m pip check
sh start.sh --version
```

On Windows, from the repository directory in Command Prompt:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r server\requirements-lock.txt
.venv\Scripts\python.exe -m pip check
START.BAT --version
```

[start.sh](../../start.sh) and [START.BAT](../../START.BAT) enter their own directory,
check the existing environment and set `PYTHONPATH` to `server/src`. They do not
install dependencies automatically. On a fresh source checkout, first copy
`server/gateway.example.json` to `server/gateway.local.json` and
`server/provider.example.cfg` to `server/provider.local.cfg`, then fill in the
fields using the native setup guide for [Windows](../en/install-windows.md),
[macOS](../en/install-macos.md) or [Linux](../en/install-linux.md), and the
[provider guide](../en/providers.md). Runtime start is
`sh start.sh --config server/gateway.local.json` or
`START.BAT --config server/gateway.local.json`. `--version` checks the starter route,
not authentication or an upstream request.

A contract-only selection, without packaging or live provider requests, is:

```sh
PYTHONPATH=server/src .venv/bin/python -B -m unittest discover -s tests -p test_provider_regressions.py
```

Other suites have their own fixtures and build prerequisites. In particular,
`test_release_packages.py` builds temporary ZIPs. Use the full
[release gate](release-process.md) for release acceptance, not this subset.

## Docker route

```sh
docker build -t ai4dos-gateway:beta .
```

[Dockerfile](../../Dockerfile) uses `python:3.12-slim-bookworm`, installs the same
lock file and runs the same Python modules as UID/GID 10001. It does not build DOS
or freeze Python into a native application. Building may fetch the base image and
dependencies. Compose supplies persistent config mounts and runtime restrictions;
Portainer uses an already built image. See [gateway listener behavior](gateway.md).
The moving base-image tag and external dependency supply are not a promise of
byte-identical Docker images. No additional host or CPU architecture is certified
by these instructions.
