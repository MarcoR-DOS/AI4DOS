# Open Watcom DOS toolchain

Tested basis: Open Watcom 2.0 beta, build 2026-09-27. WLINK reports
`Sep 27 2026 05:43:39 (32-bit)`; the compiler executables themselves use a DOS
extender, but AI4DOS output does not. Tools: binw/WCC.EXE, WPP.EXE, WASM.EXE,
WLINK.EXE; headers h/; 16-bit runtime lib286/. No lib386/ is copied.

The exact tested tree and key file fingerprints are in
[watcom-toolchain.json](watcom-toolchain.json). `tools/verify-watcom.py` checks
all three input trees before a build. These fingerprints identify the inspected
installation; they do not establish an upstream source commit or archive signature.

Official source and archived installers:
https://github.com/open-watcom/open-watcom-v2
https://github.com/open-watcom/open-watcom-v2/releases

The original installation came from a dated rolling build. The documented
upstream source reference is
[`5d6bd770b84e5f08abbd31e0990d2af5eee572d6`](https://github.com/open-watcom/open-watcom-v2/tree/5d6bd770b84e5f08abbd31e0990d2af5eee572d6),
identified by the
[September 27 daily build](https://github.com/open-watcom/open-watcom-v2/actions/runs/36297343625).
This documents the upstream build/source reference; it does not prove that the
local compiler or linked runtime binaries are byte-identical to that build.

The original GitHub Actions artifact is no longer available for an independent
byte comparison with the local toolchain. Exact historical binary-to-source
provenance therefore remains unverified. This known evidence limitation has been
accepted for the planned publication and is no longer a release blocker. The
accepted license assessment and all license obligations remain unchanged; no
additional technical proof is claimed. A current rolling download is not a
reproducible substitute, and other toolchain versions remain untested.

License: Sybase Open Watcom Public License 1.0 (`Watcom-1.0`). The toolchain is
externally supplied and not redistributed. However, AI4DOS statically links
`lib286/dos/clibl.lib`, including C startup, stdio, allocation and arithmetic
helpers. That runtime is part of the executable, not merely a build tool.

The complete license text is retained in [WATCOM-LICENSE.txt](WATCOM-LICENSE.txt)
and in the DOS ZIP as `WATCOM.TXT`. Preserve the applicable copyright and license
notices for the linked runtime. AI4DOS uses GPL-3.0-only for its own code; the
Watcom components retain their own license terms. This notice records the build
and attribution under the project's accepted toolchain assessment; it does not
grant a new runtime exception or relicense Watcom code.

Original license and runtime source:
https://github.com/open-watcom/open-watcom-v2/blob/master/license.txt
https://github.com/open-watcom/open-watcom-v2/blob/master/bld/clib/streamio/c/fopen.c

Rebuilding still requires the fingerprinted tested toolchain. Its historical
artifact provenance remains limited as described above. No replacement compiler
or runtime is introduced here. The unchanged F1 source ZIP retains the earlier
blocker wording; the [source asset notice](MTCP.md#prepared-source-release-asset)
documents that discrepancy and the current release assessment.
