# AI4DOS unter DOS einrichten

Diese Anleitung führt dich durch die Netzwerkeinrichtung, die Konfiguration von `AI4DOS.CFG` und die Bedienung des DOS-Clients. Entpacke das DOS-Paket wie im [Quick Start](quick-start.md#4-richte-ai4dos-auf-dem-dos-pc-ein) beschrieben; für die Verbindung zum Gateway braucht dein DOS-PC ein funktionierendes Netzwerk.

Beginne bei [bereits funktionierendem Netzwerk](#a-netzwerk-läuft-schon) oder [richte das Netzwerk neu ein](#b-netzwerk-neu-einrichten). Danach folgen die [Client-Konfiguration](#c-dos-client-konfigurieren-ai4doscfg) und die [Bedienung](#dos-client-bedienen).

AI4DOS unterstützt folgende DOS-Netzwerklösungen:

- PicoMEM
- NE2000-kompatible Netzwerklösungen
- jeweils in Verbindung mit mTCP

Andere Packet-Driver-kompatible Netzwerklösungen können ebenfalls funktionieren. Dafür können wir jedoch keine vollständige Kompatibilität garantieren.

## A. Netzwerk läuft schon

Wenn dein DOS-PC mit mTCP bereits andere Rechner im Netzwerk erreicht, musst du hier nichts weiter einrichten.

Prüfe nur:

- dein Packet Driver ist geladen
- mTCP funktioniert
- dein DOS-PC kann den Rechner erreichen, auf dem der AI4DOS Gateway läuft

Wenn das passt, folge der [DOS-Client-Konfiguration](#c-dos-client-konfigurieren-ai4doscfg) und starte:

```dos
AI4DOS
```

Falls dein DOS-PC noch keine funktionierende Netzwerkverbindung hat, geht es hier weiter.

---

## B. Netzwerk neu einrichten

Wir gehen jetzt Schritt für Schritt vor:

1. Netzwerkkarte oder PicoMEM vorbereiten
2. Packet Driver laden
3. mTCP einrichten
4. IP-Adresse beziehen
5. Verbindung testen
6. AI4DOS verbinden

Dabei ändern wir immer nur eine Sache nach der anderen. So lässt sich leichter erkennen, an welcher Stelle etwas nicht funktioniert.

### 1. Was ist ein Packet Driver?

Unter DOS gibt es normalerweise keinen zentralen Netzwerkdienst wie bei modernen Betriebssystemen.

Programme wie mTCP oder AI4DOS sprechen stattdessen über einen sogenannten **Packet Driver** mit der Netzwerkkarte.

Vereinfacht:

```text
AI4DOS / mTCP
      |
Packet Driver
      |
Netzwerkkarte / PicoMEM
      |
   Netzwerk
```

Der Packet Driver muss deshalb geladen sein, bevor mTCP oder AI4DOS das Netzwerk verwenden können.

### 2. Netzwerkhardware vorbereiten

#### PicoMEM

Wenn du PicoMEM verwendest, aktiviere dort die NE2000-Netzwerkemulation.

AI4DOS funktioniert mit PicoMEM und dessen NE2000-Emulation.

Die genaue I/O-Adresse und der IRQ hängen von deiner PicoMEM-Konfiguration ab.

Eine typische Konfiguration kann zum Beispiel sein:

```text
I/O 300h
IRQ 3
```

Entscheidend ist nicht, dass du exakt diese Werte verwendest, sondern dass:

- PicoMEM und Packet Driver dieselbe I/O-Adresse verwenden
- der IRQ nicht mit anderer Hardware kollidiert

#### NE2000-kompatible Netzwerkkarte

Bei einer echten NE2000-kompatiblen ISA-Karte musst du ebenfalls wissen:

- I/O-Adresse
- IRQ

Typische Werte sind beispielsweise:

```text
I/O 300h
IRQ 3
```

oder andere Kombinationen, je nach Karte und Rechner.

Wenn die Karte Jumper oder ein eigenes Setup-Programm besitzt, müssen die dort eingestellten Werte mit dem Packet Driver übereinstimmen.

### 3. Packet Driver laden

Der Packet Driver stellt die Schnittstelle zwischen Netzwerkkarte und DOS-Programmen bereit.

Viele Packet Driver werden ungefähr so gestartet:

```dos
PACKET.COM 0x60
```

oder bei einer NE2000-kompatiblen Karte sinngemäß mit zusätzlichen Angaben für I/O und IRQ.

Bei PicoMEM kann zum Beispiel der mitgelieferte Packet Driver verwendet werden.

Wichtig ist die Zahl:

```text
0x60
```

Das ist der sogenannte **Software-Interrupt**, über den DOS-Programme den Packet Driver erreichen.

Für AI4DOS und mTCP ist `0x60` ein sinnvoller und üblicher Wert.

Wenn der Packet Driver erfolgreich geladen wurde, sollte er normalerweise eine kurze Statusmeldung ausgeben.

Falls bereits hier ein Fehler erscheint, zuerst diesen lösen. mTCP kann ohne funktionierenden Packet Driver nicht arbeiten.

### 4. mTCP bereitstellen

AI4DOS verwendet mTCP für die Netzwerkkommunikation.

Lege die mTCP-Programme zum Beispiel in einen eigenen Ordner:

```text
C:\MTCP
```

Dort findest du je nach mTCP-Paket Programme wie:

```text
DHCP.EXE
PING.EXE
FTP.EXE
```

Für die Einrichtung brauchen wir zunächst hauptsächlich:

- `DHCP`
- `PING`

Wechsle für die folgenden DHCP- und PING-Befehle in diesen Ordner:

```dos
CD \MTCP
```

### 5. MTCPCFG festlegen

mTCP speichert seine Netzwerkeinstellungen in einer Konfigurationsdatei.

Dafür verwendet es die Umgebungsvariable:

```text
MTCPCFG
```

Zum Beispiel:

```dos
SET MTCPCFG=C:\MTCP\MTCP.CFG
```

Damit weiß mTCP, wo die Netzwerkkonfiguration gespeichert werden soll.

Du kannst diese Zeile später in deine `AUTOEXEC.BAT` übernehmen. Für den ersten Test reicht es aber, sie manuell einzugeben.

Prüfen kannst du die Variable mit:

```dos
SET
```

Dort sollte anschließend etwas wie:

```text
MTCPCFG=C:\MTCP\MTCP.CFG
```

erscheinen.

Lege die über `MTCPCFG` angegebene Datei `MTCP.CFG` an, falls sie noch nicht existiert.

In `MTCP.CFG` muss zusätzlich der Software-Interrupt deines Packet Drivers eingetragen sein. Wenn dein Packet Driver beispielsweise mit `0x60` geladen wurde, trage in `MTCP.CFG` ein:

```text
PACKETINT 0x60
```

Wenn du einen anderen Software-Interrupt verwendest, trage dort entsprechend diesen Wert ein.

### 6. IP-Adresse automatisch beziehen

Wenn dein Netzwerk einen normalen Router mit DHCP verwendet, ist dies der einfachste Weg.

Starte:

```dos
DHCP
```

mTCP versucht nun, automatisch:

- eine IP-Adresse
- Netzmaske
- Gateway
- DNS-Server

von deinem Router zu beziehen.

Wenn alles funktioniert, wird die Konfiguration in der über `MTCPCFG` angegebenen Datei gespeichert.

Ein erfolgreiches Ergebnis sieht sinngemäß so aus:

```text
IP address received
Gateway received
DNS server received
```

Die genaue Ausgabe kann je nach mTCP-Version abweichen.

### 7. Wenn DHCP nicht funktioniert

Falls `DHCP` keinen Server findet oder mit einem Fehler endet, prüfe zuerst:

#### Packet Driver geladen?

Der Packet Driver muss vor `DHCP` gestartet worden sein.

#### Richtiger Software-Interrupt?

Wenn dein Packet Driver auf `0x60` läuft, muss mTCP diesen auch erreichen können.

#### Stimmen I/O-Adresse und IRQ?

Bei NE2000/PicoMEM müssen die Werte zur tatsächlichen Hardwarekonfiguration passen.

#### Netzwerkkabel / Verbindung

Bei echter Ethernet-Hardware:

- Kabel eingesteckt?
- Link-LED vorhanden?
- Switch/Router-Port aktiv?

Bei PicoMEM entsprechend prüfen, ob die Netzwerkfunktion aktiv ist.

#### Hardwarekonflikte

Gerade bei alten PCs können IRQ- oder I/O-Konflikte auftreten.

Wenn zum Beispiel zwei Karten denselben IRQ verwenden, kann eine davon scheinbar funktionieren und trotzdem unzuverlässig reagieren.

### 8. Lokales Netzwerk testen

Sobald DHCP funktioniert, testen wir zuerst das lokale Netzwerk.

Finde die IP-Adresse deines Routers heraus.

Typische Beispiele:

```text
192.168.0.1
192.168.1.1
```

Dann:

```dos
PING 192.168.0.1
```

Wenn Antworten kommen, funktioniert bereits:

- Netzwerkkarte
- Packet Driver
- mTCP
- lokale IP-Konfiguration
- Verbindung zum Router

Das ist der wichtigste erste Test.

### 9. Gateway-Rechner anpingen

Jetzt teste den Rechner, auf dem der AI4DOS Gateway läuft.

Wenn dessen IP-Adresse zum Beispiel:

```text
192.168.0.42
```

lautet:

```dos
PING 192.168.0.42
```

Wenn auch dieser Ping funktioniert, kann dein DOS-PC den Gateway-Rechner grundsätzlich erreichen.

Genau diese IP-Adresse kommt später in `AI4DOS.CFG`.

### 10. Internetzugang testen

Dieser Schritt ist für AI4DOS selbst nicht zwingend erforderlich, kann aber bei der Fehlersuche helfen.

Zum Beispiel:

```dos
PING google.com
```

Wenn ein Hostname funktioniert, weißt du zusätzlich, dass DNS korrekt eingerichtet ist.

Falls:

```dos
PING 8.8.8.8
```

funktioniert, aber:

```dos
PING google.com
```

nicht, liegt das Problem wahrscheinlich bei DNS und nicht bei der Netzwerkkarte.

Für AI4DOS reicht es allerdings aus, wenn dein DOS-PC den Gateway per IP-Adresse erreichen kann.

### 11. Einstellungen dauerhaft machen

Wenn alles funktioniert, übernimm die nötigen Startbefehle in deine `AUTOEXEC.BAT`: zuerst den Packet Driver, danach `MTCPCFG` und bei dynamischer IP anschließend DHCP.

Zum Beispiel sinngemäß:

```dos
C:\MTCP\PACKET.COM 0x60
SET MTCPCFG=C:\MTCP\MTCP.CFG
C:\MTCP\DHCP.EXE
```

Ersetze die Packet-Driver-Zeile durch den zu deiner Netzwerkkarte passenden Befehl mit dem tatsächlichen Pfad und den nötigen Parametern. DHCP muss nach jedem DOS-Start erfolgreich eine IP-Konfiguration beziehen, bevor du AI4DOS startest.

Bei einer bewusst statisch eingerichteten IP-Konfiguration stehen die passenden Werte für IP-Adresse, Netzmaske, Gateway und DNS bereits in `MTCP.CFG`. Dann lässt du den DHCP-Aufruf weg; Packet Driver und `MTCPCFG` bleiben erforderlich.

### 12. AI4DOS konfigurieren

Fülle `AI4DOS.CFG` wie in der [DOS-Client-Konfiguration](#c-dos-client-konfigurieren-ai4doscfg) beschrieben aus.

Anschließend:

```dos
AI4DOS
```

Wenn alles funktioniert, erscheint oben rechts:

```text
ONLINE
```

Damit ist dein DOS-PC vollständig mit dem AI4DOS Gateway verbunden.

---

## C. DOS-Client konfigurieren (AI4DOS.CFG)

Die kommentierte Vorlage `AI4DOS.CFG` liegt im DOS-Paket neben `AI4DOS.EXE`. Bearbeite sie mit einem normalen Texteditor, speichere sie als `AI4DOS.CFG` und wechsle vor dem Start in dieses Verzeichnis. Der normale Aufruf `AI4DOS` lädt die Datei automatisch aus dem **aktuellen Verzeichnis**; ein Config-Dateiname ist nicht nötig.

Du kannst auch eine andere Konfigurationsdatei als erstes Argument laden, etwa für einen zweiten Gateway oder eine Testumgebung:

```dos
AI4DOS TEST.CFG
```

Verwende DOS-8.3-Dateinamen ohne Leerzeichen. Ein Pfad wie `C:\AI4DOS\TEST.CFG` ist ebenfalls möglich; relative Pfade beziehen sich auf das aktuelle Verzeichnis. Die Providerwahl bleibt auf dem jeweiligen Gateway.

Beispiel für einen Gateway unter `192.168.0.42` mit Standardport:

```ini
SERVER=192.168.0.42
PORT=1983
DEVICE=dos-pc
SECRET=<dein Device-Key>
LANGUAGE=de
```

Ersetze Adresse und Key durch deine eigenen Werte:

| Eintrag | Bedeutung |
| --- | --- |
| `SERVER` | Vom DOS-PC erreichbare IP-Adresse des Gateway-Rechners bzw. Docker-Hosts. Nicht die DOS-IP, die Container-IP oder die Bindadresse `0.0.0.0`; `127.0.0.1` würde auf den DOS-PC selbst zeigen. |
| `PORT` | Nativ: Listener-Port aus der Gateway-Konfiguration. Docker / Portainer: veröffentlichter Host-Port. Standard `1983`; der interne Docker-Port bleibt `1983`. Auch die Firewall muss den gewählten Port erlauben. |
| `DEVICE` | Device-ID aus dem Gateway-Bereich `devices`, für einen einzelnen DOS-PC normalerweise `dos-pc`. |
| `SECRET` | Device-Key des passenden `devices`-Eintrags, auf beiden Seiten zeichenweise identisch. Verwende mindestens 12–16 zufällige Buchstaben und Zahlen, gerne mehr, und keinen anderweitig verwendeten Key. |
| `LANGUAGE` | `de` oder `en` für Menüs, Hinweise und Fehlermeldungen des DOS-Clients. |

Der Device-Key authentifiziert den DOS-PC per HMAC; er verschlüsselt den Chatverkehr zwischen DOS-PC und Gateway nicht. Der Provider-API-Key bleibt ausschließlich auf dem Gateway und gehört niemals in `AI4DOS.CFG`.

`LANGUAGE` wählt nur die Oberfläche. Das Gateway weist das Modell an, in der Sprache deiner Nachricht zu antworten, sofern du nicht ausdrücklich eine andere Sprache verlangst. Schreibe also in der gewünschten Antwortsprache. Der Client ist textbasiert und kann keine Bilder oder Dateien anzeigen oder hochladen; das Gateway erklärt dem Modell diese Grenzen.

Nach Änderungen an `AI4DOS.CFG` starte AI4DOS neu. Bereits gespeicherte Chatdateien werden dadurch nicht verändert. Für den Einstieg bleiben erweiterte Netzwerk-, Puffer-, Session- und Authentifizierungseinstellungen auf ihren Standardwerten.

### Mehrere DOS-Geräte

Ein Gateway kann mehrere DOS-Rechner bedienen. Ergänze dafür je eine Device-ID mit eigenem Device-Key im bestehenden `devices`-Objekt: nativ in `server/gateway.local.json`, bei Docker / Portainer in `config.local/gateway.json`.

```json
"devices": {
  "ibm-xt": "<Key fuer den XT>",
  "486dx2": "<Key fuer den 486>"
}
```

Ersetze beide Key-Platzhalter durch eigene zufällige Werte ohne Leerzeichen. Trage auf jedem DOS-PC die zugehörige ID bei `DEVICE=` und ihren Key bei `SECRET=` ein. Speichere die Dateien und starte Gateway und DOS-Clients neu. Für einen einzelnen DOS-PC genügt der vorhandene Eintrag `dos-pc`.

## Fehler Schritt für Schritt eingrenzen

Wenn es nicht funktioniert, teste immer in dieser Reihenfolge:

```text
1. Packet Driver lädt?
        |
2. DHCP funktioniert?
        |
3. Router-Ping funktioniert?
        |
4. Gateway-Ping funktioniert?
        |
5. AI4DOS verbindet sich?
```

So weißt du schnell, in welchem Bereich der Fehler liegt.

### Packet Driver lädt nicht

Problem liegt wahrscheinlich bei:

- Netzwerkkarte
- I/O-Adresse
- IRQ
- Packet Driver

### DHCP funktioniert nicht

Problem liegt wahrscheinlich bei:

- Packet Driver
- Netzwerkverbindung
- Router/DHCP
- Hardwarekonflikt

### Router-Ping funktioniert, Gateway-Ping nicht

Problem liegt wahrscheinlich zwischen DOS-PC und Gateway-Rechner, zum Beispiel:

- falsche Gateway-IP
- Firewall
- falsches Netzwerk/VLAN

### Gateway-Ping funktioniert, AI4DOS bleibt offline

Dann funktioniert das DOS-Netzwerk grundsätzlich.

Prüfe jetzt:

- läuft der AI4DOS Gateway?
- stimmt dessen Port?
- stimmt der Device-Key auf beiden Seiten?
- stimmt die Gateway-IP in `AI4DOS.CFG`?
- blockiert eine Firewall TCP-Port 1983?

→ [AI4DOS Fehlerbehebung](troubleshooting.md)

## DOS-Client bedienen

Starte nur `AI4DOS`. Systemmeldungen erscheinen im Chatbereich; oben rechts steht der Verbindungsstatus.

| Taste / Befehl | Funktion |
| --- | --- |
| Enter | Nachricht senden |
| F1 / `/info` | Produktversion, Wire-Version und Session anzeigen |
| F2 / `/new` | Neuen Chat beginnen |
| F4 / `/help` | Hilfe anzeigen |
| F5 / `/save` | Chat unter `CHATS\` speichern (DOS-8.3-Dateiname) |
| F10 / `/quit` | Beenden; mit F10 bestätigen, mit Esc abbrechen |
| PgUp / PgDn | Seitenweise im sichtbaren Verlauf blättern |
| Pfeil hoch / runter | Zeilenweise blättern |
| Esc | Zurück zum Chat |
| `/reconnect` | Neu verbinden und vorhandene Session fortsetzen |

Der sichtbare Scrollback umfasst 128 Zeilen. Der gespeicherte Transcript kann länger sein; eine neue Session löscht den aktuellen Chat. Sessions liegen im Gateway-Arbeitsspeicher: Nach einem Gateway-Neustart lässt sich die alte Session nicht wiederherstellen. `LANGUAGE=en` bzw. `LANGUAGE=de` in `AI4DOS.CFG` wählt die Sprache; nach einer Änderung den Client neu starten.

Packet Driver und mTCP-Werkzeuge sind separate Netzwerkvoraussetzungen und werden nicht im DOS-ZIP mitgeliefert. Die Anleitung ersetzt keine treiber- oder hardwarespezifische Dokumentation.
