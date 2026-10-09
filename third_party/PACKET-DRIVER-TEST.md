# External packet driver used for emulator tests

The DOS network test accepts a separately supplied Crynwr NE2000-compatible
packet driver through `NE2K_DRIVER`; it is not linked or redistributed here.
The locally inspected Crynwr distribution metadata identifies 2006-09-02c,
while README.11C describes the 11.x supplement. The inspected NE2000.ASM
identifies driver version 4, copyright 1988–1992 Russell Nelson / Crynwr,
and explicitly states GNU GPL version 1. Metadata saying only “Open source”
is not used as a license conclusion. AI4DOS uses GPL-3.0-only; the external driver retains its own grant.

For the current DOSBox-X 8086 test, a separately prepared driver uses 8086
word-I/O loops for two NE2000 remote-DMA transfers. Its SHA256 is
`f95b36199a47bf7e6eb03cb9474e97d50cb9c23de08996a036bb525599e0b9f2`.
Packed input NE2000.COM SHA256:
`f8b4cb8d1b93210045c591e23d21f8043a5397a5769e52ca68ffdadc7a85a5cd`.
Inspected source archive SHA256:
`7f18ad299099e0756f89ad96c816a220d53fa5f650a5e22bc1bca2aa9ca994d9`.
The prepared binary is copied only into ignored test artifacts. This emulator
workaround is not hardware validation or a universal driver recommendation.
[Collection site](http://crynwr.com).

Before distributing any packet driver: establish its complete corresponding
source and notices separately. No driver is included in public project files.
