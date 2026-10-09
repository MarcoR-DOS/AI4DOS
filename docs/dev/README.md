# Developer documentation

This documentation describes the source tree in this checkout. It covers implementation and
maintenance; the [project overview](../../README.md) and
[public user documentation](../README.md) cover use and installation.
Commands assume the repository root unless stated otherwise.

| Page | Contents |
| --- | --- |
| [Architecture](architecture.md) | Component boundaries, data flow, transport and session state |
| [Building](building.md) | Pinned DOS toolchain, host checks, Python environment and Docker |
| [DOS client](dos-client.md) | UI, memory, networking, encoding, transcript and save behavior |
| [Gateway](gateway.md) | Authentication, session ownership, configuration and limits |
| [Providers](providers.md) | Adapter contract, reasoning options, stream completion and errors |
| [Release process](release-process.md) | Package inputs, reproducibility, mandatory gate and validation scope |
| [Contributing](contributing.md) | Focused changes, regression checks and review evidence |

## Source map

- `client/src/` and `client/include/`: DOS C/C++ implementation and interfaces;
  `client/tests/`: bounded client checks.
- `server/src/ai4dos/`: Python gateway, configuration, sessions and adapters;
  `tests/`: Python contracts plus the native test transport.
- `tools/`: host/DOS build wrappers, setup helpers, packaging and validation.
- `release/inputs/`: pinned DOS binary and source/build fingerprint manifest.
- `protocol/`: the separate [Wire Protocol](../../protocol/README.md).
- `third_party/`: toolchain fingerprints, dependency provenance and notices.

Implementation statements come from these sources. Build and release checks
must record their tested scope; a passing build does not certify every model or host.
Maintainer-reported hardware results are identified separately. Unknown upstream
model behavior and unsupported host/toolchain combinations remain open or
implementation-specific. There is no separate architecture specification in this
baseline; [architecture.md](architecture.md) maps the current implementation.
