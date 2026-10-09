# Contributing to the implementation

[Developer index](README.md) · [Building](building.md) · [Release process](release-process.md)

The maintainer decides scope, acceptance and release readiness. The existing
[root contribution guide](../../CONTRIBUTING.md) notes that a formal public
contribution route will follow with beta. These expectations describe useful
review material; they do not create a new release or approval workflow.

## Keep a change reviewable

Prefer small, focused PRs with a concrete trigger, resulting behavior and evidence.
Agree on substantial design work first. Keep unrelated refactors out of bug fixes.
Preserve UI behavior unless the change is deliberate and documented: header states,
normal footer, scroll indicators, overlays, role/label separation, save confirmation
and new-chat/resume semantics are part of the existing user experience.

For a bug fix, include a regression test that reproduces the failure and checks
observable behavior. Choose checks for the actual changed path rather than testing
an unrelated platform or mirroring the implementation. Documentation-only changes
normally need source/path/link/whitespace checks, not rebuilt packages or new live
provider requests. Record prerequisites and limits when a check cannot run.

## Compatibility and secrets

Client work must preserve 8086/8088 real-mode compatibility unless the maintainer
explicitly changes the target. Check `-0`, memory model, far-pointer boundaries,
integer widths, stack use and linked runtime. Do not introduce hidden 186+/286+
instruction, flat-memory or modern BIOS assumptions. Use host checks for logic,
DOS builds/runtime checks for the actual compiler path, and distinguish physical
hardware observations from emulator evidence. Follow the current
[build route](building.md), not an assumed modern C toolchain.

Never put API keys, device secrets, HMAC/auth captures, private configs, chat dumps
or credential-bearing API bodies into issues, logs, screenshots or fixtures.
Synthetic errors must use harmless sentinel data. Report secret scans as counts/
paths without printing values. Keep attribution, licenses and dependency pins;
consult [third-party notices](../../THIRD_PARTY_NOTICES.md) before claiming
redistribution rights.

Provider changes must update tests and release-gate coverage, including options,
labels, terminal success, safe errors and cleanup. Adding a module also requires
its explicit packaging input. See [adding a provider](providers.md) and retain the
existing OpenRouter/OpenAI/Mistral regressions. Offline contracts prove the fixture
behavior; live support claims need separately recorded, model-specific evidence.

## Review handoff

Include the behavior changed and why, files/scope, regression evidence, commands
actually run, results and remaining limitations. Separate fresh results from older
reports and maintainer observations. Check relative Markdown links and
`git diff --check`; inspect the final diff for private data and unrelated files.
Use the [mandatory gate](release-process.md#mandatory-offline-gate) for a release,
with live checks enabled only when explicitly intended. A commit, a push and a
publication are separate actions and must follow the agreed scope.

Disclose AI-assisted implementation transparently in the contribution description
when applicable. Explain what was reviewed and tested; AI-generated output is
subject to the same compatibility and evidence requirements. Contributors do not
need to use AI tools.
