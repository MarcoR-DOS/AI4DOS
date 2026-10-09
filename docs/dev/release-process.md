# Release process

[Developer index](README.md) · [Building](building.md) · [Providers](providers.md)

## Documentation and package boundary

Canonical published user documentation lives in [docs/de and docs/en](../README.md).
Developer documentation must reflect the current implementation. The main README stays
a project overview. Protocol details stay in the
[Wire Protocol](../../protocol/README.md); release acceptance stays in the
[mandatory offline gate](#mandatory-offline-gate).

[package-release.py](../../tools/package-release.py) explicitly selects inputs:

| Target | ZIP | Runtime contents |
| --- | --- | --- |
| dos | AI4DOS-DOS.zip | Pinned DOS EXE, AI4DOS.CFG with placeholder, VERSION.TXT, GPL text, third-party notices and Watcom license |
| windows | AI4DOS-Server-Windows.zip | Shared gateway source/locked requirements, local-named placeholder configs, START.BAT, version/legal files |
| macos | AI4DOS-Server-macOS.zip | Same gateway inputs, start.sh |
| linux | AI4DOS-Server-Linux.zip | Same gateway inputs, start.sh |
| docker | AI4DOS-Server-Docker.zip | Same gateway inputs, Dockerfile/Compose/Portainer/.dockerignore/healthcheck, config.local placeholders |

Packages intentionally omit package README/Quickstart/START-HERE, `.env`, example
files, public docs, tests, private configs, logs and virtual environments. Repository
example configs are reviewed *inputs*, shipped under editable local runtime names.
This is not missing installation documentation: installation comes from the
canonical public docs. Packet Drivers, separate mTCP tools and Watcom are not
bundled. Python packages contain source, not a frozen interpreter. The Docker ZIP
contains build inputs, not a prebuilt image.

## Provenance and reproducibility

`release/inputs/AI4DOS.EXE` is the package's DOS binary input, not a fresh local
`client/build/AI4DOS.EXE`. [dos-build.json](../../release/inputs/dos-build.json)
records source/build/toolchain fingerprints, mTCP pin and binary SHA256.
`verify_dos_input()` rejects changed pinned inputs rather than silently accepting a
new client binary. A DOS change therefore requires a separately validated rebuild
and deliberate provenance update. Product-version checks bind VERSION to the DOS
binary and gateway __version__.

ZIP members are sorted, timestamps fixed at 1980-01-01, permissions fixed and
compression level fixed. Reproducibility is byte-for-byte for identical inputs and
the same Python/zlib toolchain; it does not promise identical output across every
compressor or a reproducible Docker image. Templates undergo credential-placeholder
checks; symlinked inputs are refused. Docker gateway config is transformed to the
internal listener/provider-file layout. Native configs receive private file modes;
placeholder Docker configs are readable by container UID 10001.

Fresh gate hashes live in `dist/release-gate.json`. Associate published hashes
with the exact delivered artifacts; check inputs and ZIP module parity before
calling them a current-source release.

When packaging is explicitly in scope, local build commands are:

```sh
python3 tools/package-release.py all --output dist
```

Individual target names are `dos`, `windows`, `macos`, `linux`, `docker`.
This builds ZIPs; it does not publish. Do not run it for a docs-only task that
forbids artifact rebuilds.

## Mandatory offline gate

Before a gateway/beta release, run from the repository root:

```sh
.venv/bin/python -B tools/validate-release.py
```

Prerequisites are a POSIX developer host, locked Python environment, `cc`, and
running Docker with Compose. The [implementation](../../tools/validate-release.py)
builds the minimal host transport client, runs required contracts with no skips,
checks DOS provenance, builds/recompares packages, scans credential patterns,
checks package/source parity and imports, and executes starter/mock-chat smokes.
It also starts a fresh Docker image from the ZIP, checks health, mock chat and
runtime restrictions with `network=none` and no published host ports, checks
Compose/Portainer syntax, cleans temporary containers/images, and runs
`git diff --check`. Missing prerequisites fail the gate.

The default run makes no external provider requests, removes inherited provider
key/AI4DOS environment settings for offline execution and blocks external DNS/TCP
in Python contract tests. Docker image/dependency acquisition can still use a
registry/package index. The gate creates ZIPs and writes a report in `dist/`;
**it is not a read-only documentation check**.

Do not run this full gate when authorized scope forbids ZIP rebuilds. For docs-only
changes, check references, commands against source, scope and whitespace; explicitly
report that the release gate was not run. Package contract tests also build ZIPs.
A focused documentation validation is not a replacement for release acceptance.

## Optional live smoke and durable regressions

Live requires explicit enablement and a private config path, never a key argument:

```sh
.venv/bin/python -B tools/validate-release.py --live-config /absolute/private/gateway.json
```

Repeat the flag only for different providers. The live config must explicitly cap
MAX_OUTPUT_TOKENS at 256 or less; 128 with REASONING=none is the documented smoke
setting. The gate permits one generation request per provider, no retry/model
substitution, and requires visible DATA plus END. It does not make metadata probes.
OFFLINE PASS means the selected offline checks passed; LIVE PASS means an
explicit live smoke passed. LIVE NOT AVAILABLE means the check was not requested
or access/model availability was missing; FAIL means a required check failed.
Unrequested or unavailable live access is not certified support. No live requests
are implied by a present key.

The following cases must remain in gate coverage:

- OpenRouter usage-only final chunk repeating stop: accepted once with usage;
  late content and invalid terminals remain errors.
- OpenAI Responses error/response.failed: preserve safe auth/model/rate/unavailable
  categories rather than flattening them to UPSTREAM; discard raw error text.
- Mistral thinking/text content lists: hide validated thinking, emit text, reject
  malformed/nontext blocks and output after completion.
- Gemini exact native URL/header, explicit known-model off mapping, 404 normalization,
  STOP/usage/thought/transport/cleanup behavior. This is offline evidence, not
  gemini-2.5-flash live success.
- Shared config/factory, arbitrary model IDs, provider labels, capability prompt,
  reasoning defaults, stream completion, secrets and native Claude contracts.
- Gate safeguards for offline network access, secret patterns, missing keys and
  separated live result/request accounting.

Exact regression test names remain in the source test suites, avoiding
an independently maintained copy here.

## Clean-room and delta discipline

Clean-room acceptance uses the release ZIP plus canonical public docs, with no
checkout-only helper or hidden DEV configuration. Run prerequisites are documented
separately (Python, Docker, Packet Driver/network setup). Host starter contracts,
emulator observations, native OS execution and physical hardware results must be
reported distinctly. Record the tested artifact, environment, results and
unresolved boundaries for each acceptance run.

Validate the delta: documentation-only changes need documentation/link checks;
package-only changes need relevant archive/config/parity checks and affected smokes.
Do not rerun unrelated full platform or provider-live tests merely because prose
or packaging changed. A real release still requires the mandatory gate. Changed
client runtime/hardware paths need appropriate DOS checks and honest hardware
status; emulator results cannot certify a physical XT.

Preserve [Watcom attribution and license terms](../../third_party/WATCOM.md)
and [third-party obligations](../../THIRD_PARTY_NOTICES.md). Before distributing the
DOS binary, complete and verify the maintainer-hosted
[Corresponding Source delivery](../../third_party/MTCP.md#corresponding-source-for-a-downloadable-dos-binary).
Only `release/inputs/AI4DOS.EXE` and `release/inputs/dos-build.json` are public release
inputs; internal reports and historical manifests are not publication inputs.
The DOS manifest verifies content hashes, independently of AI4DOS Git history.
The gate records the current HEAD for its new report; it does not require private
ancestor commits. Do not infer publication approval from local build success.
