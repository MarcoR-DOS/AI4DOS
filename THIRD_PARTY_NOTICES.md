# Third-party notices

AI4DOS is licensed under GPL-3.0-only. This inventory describes its dependencies
and retains their respective grants and notices; it does not override them. No toolchain, packet
driver, Python environment or SDK package is bundled in the source tree.

## DOS components

- **mTCP**, Michael B. Brutman, per-file copyright dates (linked units generally
  2005–2025): https://github.com/mbbrutman/mTCP at
  `dbb161efb723da4a9eaadc7436c2110492370acd`, `GPL-3.0-or-later`.
  Selected C++/assembly sources are statically linked, with
  `tools/mtcp-cleanup.patch`. Staging preserves notices and marks changed files.
  A binary distribution needs the actual corresponding source, configuration,
  patch/build scripts and GPL text alongside its source access arrangement.
  See [mTCP](third_party/MTCP.md).
- **Open Watcom 2.0 beta, 2026-09-27**, Sybase/Open Watcom contributors:
  https://github.com/open-watcom/open-watcom-v2, `Watcom-1.0`.
  External compiler plus statically linked `lib286/dos/clibl.lib` runtime.
  Exact fingerprints, runtime attribution and the complete Watcom license are
  documented in [Watcom](third_party/WATCOM.md). This is not tool-only usage.
- **Packet driver**: separately loaded external DOS program, not linked or bundled.
  The specific Crynwr NE2000 emulator-test driver and its GPL-v1 source header
  are described in [the test-driver notice](third_party/PACKET-DRIVER-TEST.md).
  No grant for an arbitrary hardware driver is inferred from that test package.

## Gateway runtime packages

Installed separately through `server/requirements-lock.txt`; no package source
is copied into AI4DOS. Versions and licenses below were read from the installed
package metadata and included license files. Colorama is Windows-only and its
0.4.6 release/license was checked against PyPI. No Gemini/Mistral/NVIDIA-specific
SDK, dotenv package, FTP service or optional OpenAI SDK extras are required.

| Package | Version | Source | Use | License |
| --- | --- | --- | --- | --- |
| openai | 2.48.0 | [release](https://pypi.org/project/openai/2.48.0/) | OpenAI Responses and compatible Chat SDK | Apache-2.0 |
| httpx | 0.28.1 | [release](https://pypi.org/project/httpx/0.28.1/) | HTTPS and native Gemini transport | BSD-3-Clause |
| anyio | 4.12.1 | [release](https://pypi.org/project/anyio/4.12.1/) | HTTPX async runtime | MIT |
| annotated-types | 0.7.0 | [release](https://pypi.org/project/annotated-types/0.7.0/) | Pydantic metadata | MIT |
| certifi | 2026.7.22 | [release](https://pypi.org/project/certifi/2026.7.22/) | Mozilla CA certificate bundle | MPL-2.0 |
| distro | 1.9.0 | [release](https://pypi.org/project/distro/1.9.0/) | SDK platform information | Apache-2.0 |
| exceptiongroup | 1.3.1 | [release](https://pypi.org/project/exceptiongroup/1.3.1/) | AnyIO compatibility, Python <3.11 | MIT AND PSF-2.0 |
| h11 | 0.16.0 | [release](https://pypi.org/project/h11/0.16.0/) | HTTP/1.1 framing | MIT |
| httpcore | 1.0.9 | [release](https://pypi.org/project/httpcore/1.0.9/) | HTTPX connection handling | BSD-3-Clause |
| idna | 3.20 | [release](https://pypi.org/project/idna/3.20/) | Hostname encoding | BSD-3-Clause |
| jiter | 0.16.0 | [release](https://pypi.org/project/jiter/0.16.0/) | SDK JSON parsing | MIT |
| pydantic | 2.13.5 | [release](https://pypi.org/project/pydantic/2.13.5/) | SDK data models | MIT |
| pydantic_core | 2.46.5 | [release](https://pypi.org/project/pydantic_core/2.46.5/) | Pydantic native validation | MIT |
| sniffio | 1.3.1 | [release](https://pypi.org/project/sniffio/1.3.1/) | Async-library detection | MIT OR Apache-2.0 |
| tqdm | 4.70.1 | [release](https://pypi.org/project/tqdm/4.70.1/) | SDK dependency, progress support | MPL-2.0 AND MIT |
| typing-inspection | 0.4.2 | [release](https://pypi.org/project/typing-inspection/0.4.2/) | Pydantic typing introspection | MIT |
| typing_extensions | 4.16.0 | [release](https://pypi.org/project/typing_extensions/4.16.0/) | Runtime typing backports | PSF-2.0 |
| colorama | 0.4.6 | [release](https://pypi.org/project/colorama/0.4.6/) | tqdm dependency on Windows | BSD-3-Clause |

If these packages are later bundled, retain the packages' complete copyright,
license and applicable NOTICE files. MIT/BSD require their notices and disclaimer;
BSD also prohibits endorsement without permission. Apache-2.0 requires its license,
applicable notices and marking modified files. Sniffio offers either MIT or Apache.
Exceptiongroup also contains Python code with PSF notices; typing_extensions carries
Python's full license history. Certifi's CA data and tqdm's MPL-covered portions
require MPL notices and access to their covered source when distributed; MIT-covered
tqdm contributions retain MIT terms. No such package modifications are made here.
The packages' licenses are not replaced by the project's GPL variant.

## External tools and interpreter

Python >=3.9 with its standard library is the gateway runtime; use the interpreter
supplier's Python/PSF and bundled-library notices. It is not redistributed here.
DOSBox-X is a separate GPL-v2-or-later build/test emulator. Git, tar, patch,
a POSIX shell and Python orchestrate the DOS build; GNU binutils inspects it.
The native regression tests additionally use a host C compiler. None of these
programs is linked into AI4DOS or included in the proposed beta packages.
Licensing any later redistribution of those tools is a separate review.
