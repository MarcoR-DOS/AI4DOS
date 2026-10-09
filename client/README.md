# DOS-Client

`AI4DOS.EXE`: DOS-MZ, 8086/8088, Real Mode, kein DOS-Extender.
80x25-Oberfläche mit EN/DE, CP437/CP850 oder ASCII-Fallback, Transcript,
128-Zeilen-Scrollback, Save unter `CHATS\`, Reconnect und Session Resume.

## Build

Der bestehende Hostwrapper erzeugt und startet `client/build/BUILD.BAT`.
Kein zusätzliches Buildsystem. Benötigt: POSIX-Shell, Python >=3.9, Git, tar,
patch, DOSBox-X und die [festgehaltene Open-Watcom-DOS-Toolchain](../third_party/WATCOM.md).
Die Quellen von [mTCP](../third_party/MTCP.md) werden separat bereitgestellt:

```sh
git clone https://github.com/mbbrutman/mTCP /path/to/mTCP
git -C /path/to/mTCP checkout --detach dbb161efb723da4a9eaadc7436c2110492370acd
MTCP_SOURCE=/path/to/mTCP sh tools/stage-mtcp.sh
WATCOM_ROOT=/path/to/watcom DOSBOX_X=dosbox-x sh tools/build-dos.sh
GOBJDUMP=gobjdump sh tools/verify-dos.sh
```

Die `/path/to/…`-Werte sind Platzhalter. Starte die Befehle im Projektverzeichnis.
`gobjdump` ist GNU binutils (auf manchen Systemen `objdump`). Der Wrapper prüft
den mTCP-Pin und die getesteten Compiler-/Header-/Runtime-Fingerprints, kopiert
Watcom nach `client/build/watcom` und schreibt ausschließlich in den Buildbereich.
DOS-Laufwerke: C=client, D=Watcom-Kopie, E=mTCP/src. Der Compiler läuft auf einer
emulierten modernen CPU; erzeugter Code wird über `-0` auf 8086 festgelegt.

Reihenfolge: C-Clientobjekte → C++-Adapter → PACKET/ARP/ETH/IP/TCP/TCPSOCKM/
UTILS/TIMER → IPASM → `wlink @AI4DOS.LNK` → Core-/Encodingtests.
C-Flags: `-0 -ml -bt=dos -d0 -s -os -zq -i=include`.
C++-Flags via WPP (DOS-Kommandozeilenlimit): `-0 -ml -bt=dos -d0 -s -os -oh
-ok -oa -ei -ob -ol+ -oi+ -zq -zp2 -zpw -we -fi=include\mtcpcfg.h -i=include
-i=E:\TCPINC`. Assembler: `wasm -0 -ml -zq`.
Linker: `system dos`, 8192-Byte-Stack, Large Model, `lib286/dos/clibl.lib`;
keine lib386-/Extender-Runtime. `lib286` ist der Verzeichnisname für 16-Bit-Libs,
kein Beleg für ein 286-Codeziel. mTCP-Konfiguration: `include/mtcpcfg.h`, ARP/TCP,
vier Packetbuffer, ein Socket, vier TX-Puffer; keine DNS-Auflösung.

Output: `client/build/AI4DOS.EXE`, Map und `BUILD.LOG`/`BUILD.STA`.
`CORETEST.EXE` und `ENCODING.EXE` mit ihren PASS-Logs sind Prüfarbeitsprodukte.
Sie gehören nicht ins DOS-Paket. MZ/i8086-/Markerprüfung allein beweist nicht jede
Laufzeitinstruktion; `-0`, 16-Bit-Linkermap und 8086-Laufzeittests ergänzen sie.

## DOS-Aufruf

Packet Driver laden und `SET MTCPCFG=C:\NET\MTCP.CFG` für die eigene Netzwerkkonfiguration
setzen. IP-/Netzmasken-/Gatewaywerte stammen aus dem eigenen LAN; Packet Driver,
DHCP-Tool und mTCP-Programme werden nicht mit AI4DOS ausgeliefert.
Die [Beispielkonfiguration](AI4DOS.CFG.example) als `AI4DOS.CFG` kopieren und
`SERVER`, `PORT`, `DEVICE` und den eigenen `SECRET` passend zum Gateway setzen.
Wähle einen eigenen Device-Key und trage denselben Wert als `SECRET` sowie unter
`devices["dos-pc"]` in `server/gateway.local.json` bzw. bei Docker
`config.local/gateway.json` ein. Am besten mindestens 12–16 Zeichen aus Buchstaben
und Zahlen verwenden und keinen bereits anderswo benutzten Schlüssel.
Technisch sind 8–128 druckbare ASCII-Zeichen ohne Leerzeichen zulässig.
Der Platzhalter ist kein verwendbarer Schlüssel.

```text
AI4DOS
```

Enter sendet; F1 Info, F2 neue Session, F4 Hilfe, F5 speichern, F10 Exitbestätigung.
PgUp/PgDn und Up/Down scrollen; ESC schließt Dialoge. `/reconnect` verbindet neu
und versucht dieselbe Session fortzusetzen. Sessions überleben keinen Gatewayrestart;
Stream Resume ist nicht verfügbar. Save nutzt bestätigte DOS-8.3-Namen und ergänzt
`.TXT` bei extensionlosen Namen. Codepage AUTO fragt DOS ab; LANGUAGE=en/de.

Verbindungsversuch, erfolgreiche Verbindung, unerreichbares Gateway, abgelehnte
Device-Authentifizierung, Verbindungsabbruch und erfolgreiches Reconnect/Resume
erscheinen als `System:` im Chatbereich (EN/DE). Die Anzeige springt dafür ans
Verlaufsende; Scrollback und Transcript bleiben begrenzt. Diese lokalen Einträge
haben die eigene Rolle `ROLE_SYSTEM`, werden mit F5 gespeichert und niemals als
`MSG` oder Modellkontext übertragen. Die Statusanzeige bleibt unverändert.

BIOS setzt Textmodus/Cursor. Zellen gehen zentral an B000 (Modus 7) oder B800
(Modus 3); Legacy-CGA verwendet BIOS-Schreiben. Beim Exit werden Modus, Seite,
Textzeilen und Cursor restauriert; alter Bildschirminhalt und Fonts werden nicht gesichert.
Lokale Konfiguration und Chats nicht veröffentlichen.

Der Footer im normalen Chat bleibt statisch (PgUp/Dn, F2, F4, F5, F10).
Laufzeithinweise erscheinen als lokale Systemmeldungen im Chat und, sofern noch
Platz vorhanden ist, im Transcript; sie werden nicht an das Modell gesendet.
Der Headerstatus verwendet nur CONNECTING, ONLINE, TX/RX und ERROR.
