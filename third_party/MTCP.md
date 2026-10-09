# mTCP build dependency

Source: https://github.com/mbbrutman/mTCP
Pinned source commit: `dbb161efb723da4a9eaadc7436c2110492370acd`.

The local source headers inspected at this commit identify Michael B. Brutman,
2006–2025 (individual dates vary), and explicitly permit GPL version 3 or later.
The upstream `LICENSE` contains the GNU GPL v3 text. mTCP is therefore `GPL-3.0-or-later`. The inherited client grant is
`GPL-3.0-only`; combining it with mTCP under GPL v3 does not grant permission
to relicense that inherited code as or-later.

The build stages `LICENSE`, `src/TCPINC` and `src/TCPLIB` from that exact commit
into ignored `client/build/mtcp/`. Headers retain upstream notices.
Only PACKET, ARP, ETH, IP, TCP, TCPSOCKM, UTILS, TIMER and IPASM are linked.
No upstream application, deployment or credential is included in the client.

`tools/mtcp-cleanup.patch` is a selected cleanup adjustment for packet/TCP/socket
pool pointers and the Watcom far-model heap diagnostic. It changes dependency
code only in the ignored staged tree. The base plus patch are needed to reproduce
the build; the patch is a modification of GPL-covered mTCP code, not a relicensing.
The build also needs a separately provided classic Packet Driver and Open Watcom.
Neither a packet-driver distribution nor Watcom redistribution is included here.

## Corresponding Source for a downloadable DOS binary

The release route is a versioned, maintainer-hosted source archive alongside the
DOS ZIP, with equivalent download access at no additional charge (GPL v3 section
6(d)). An upstream commit link alone is not the release's source delivery.

Prepare the archive from reviewed inputs, not from the ignored build directory:

- AI4DOS client source and headers, linker file, configuration, build/staging and
  verification scripts, toolchain fingerprints and build instructions from the
  matching source snapshot; retain their notices and the complete GPL text.
- mTCP `LICENSE`, `src/TCPINC` and `src/TCPLIB`, exported from the pinned upstream
  commit with `git archive`, exactly as `tools/stage-mtcp.sh` selects them.
- `tools/mtcp-cleanup.patch` and the staging script, including the dated modification
  notices it adds to four upstream files. The unmodified base plus these scripts
  reconstructs the modified source used for the build.

Keep the archive versioned with the binary and record its hash. Verify the source
headers/license, include closure and clean build against the pinned EXE before
approving this as the complete release source. Instructions must identify the
external toolchain and any required runtime source provision under its applicable
terms; this preparation does not change the accepted Watcom assessment.

**Release prerequisite:** a reviewed local checkout/archive of the pinned mTCP
source must be approved for export, and the complete source archive must be built,
reviewed and made available with the DOS binary. No upstream source archive is
included or newly downloaded in this preparation. No source-download URL or
availability is claimed until that delivery exists. See the
[release process](../docs/dev/release-process.md) and
[build instructions](../docs/dev/building.md).

## Prepared source release asset

The separately prepared asset for AI4DOS 0.1.0-beta.1 is
`AI4DOS-DOS-Source-Beta-2026-10-09-F1.zip` (94 files).

- Source archive SHA256: `d9a324cf228ecedf8172892e5ed78a38718995696e7b047fe1161746315356a9`.
- Matching DOS binary SHA256: `55b6aef3fb43baecbd960f5f6ea19ba82ccd5817c5d025dceff35f35cf65abad`.
- mTCP base: `dbb161efb723da4a9eaadc7436c2110492370acd`; patch:
  `e953e8a6715d1fccaadf82b39c9bb6a963e72c0d880006a8e90f549895cd428f`.

The archive has 92 input hashes in `SOURCE-MANIFEST.json`; `SHA256SUMS`
contains 93 entries, including the source manifest. Together with `SHA256SUMS`,
these are the 94 archive files.

The asset contains the matching client inputs, unmodified pinned TCPINC/TCPLIB
export and GPL text, patch and dated modification notices, offline staging helper,
build instructions and Watcom license/fingerprints. It contains no compiler or
runtime binary. Its existing isolated rebuild reproduced the matching DOS binary;
that evidence does not replace acceptance of a build from this new repository.

Keep this archive as a separate source release asset, rather than importing the
upstream source tree into Git. Before binary publication, recheck its manifests,
source-to-binary association and notices against the final release, then provide
it beside the matching binary with equivalent download access at no extra charge
under the already selected GPL v3 section 6(d) route. No public availability or
final download URL is claimed here.

The known Watcom provenance limitation has been accepted for the planned
publication; see [Watcom provenance](WATCOM.md). This release decision does not
establish an exact binary-to-source mapping or change any license obligations.

The source ZIP is retained unchanged with the SHA256 above. Its
`third_party/WATCOM-PROVENANCE.json` still records
`exact_binary_source_mapping: "BLOCKED"`, and `README-SOURCE.md` still calls the
missing historical artifact comparison a release blocker. Those statements
reflect the earlier release assessment and are superseded by the accepted
provenance limitation documented here. The technical evidence remains limited:
the exact historical compiler/runtime artifact bytes were not independently
matched to the local installation. No additional proof is claimed.
