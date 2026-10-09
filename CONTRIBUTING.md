# Contributing

Clear bug reports, documentation improvements and small PRs are welcome.
For larger changes, discuss the proposed benefit first. The maintainer decides
scope, acceptance and release readiness.

The client targets 16-bit DOS and 8086/8088 systems with Open Watcom, the large
memory model and far pointers. Keep conventional RAM limits, codepages,
mTCP/Packet Driver requirements and 8088 performance in mind.

Keep diffs focused and check the actual build or runtime path affected by a
change. Include a regression test for bug fixes, and distinguish emulator
results from observations on real hardware. Documentation changes normally
need only source, link and formatting checks.

Never include API keys, device secrets, authentication captures, private
configuration, logs containing secrets or chat histories. Preserve third-party
licenses and attribution.

The [mandatory offline gate](docs/dev/release-process.md#mandatory-offline-gate)
must pass before a gateway or beta release: `.venv/bin/python -B tools/validate-release.py`.
The default run makes no live provider requests. Run live smoke tests only
when explicitly authorized.

See the [developer contribution guide](docs/dev/contributing.md) for details,
the [client README](client/README.md) for build instructions and the
[user documentation](docs/README.md) for setup.
