# AI4DOS Fehlerbehebung

Wenn AI4DOS nicht funktioniert, geh am besten immer **vom einfachsten zum wahrscheinlichsten Fehler** vor.

Die wichtigste Regel lautet:

> Erst prüfen, **wo** die Verbindung scheitert – DOS-PC, Netzwerk, Gateway oder KI-Anbieter.

## 1. AI4DOS startet nicht

### `AI4DOS.CFG` wurde nicht gefunden

Wenn `AI4DOS.EXE` seine Konfigurationsdatei nicht findet, erscheint eine englische Fehlermeldung.

Prüfe:

- liegt `AI4DOS.CFG` im selben Verzeichnis wie `AI4DOS.EXE`?
- heißt die Datei wirklich exakt `AI4DOS.CFG`?
- wurde sie versehentlich als `AI4DOS.CFG.TXT` gespeichert?
- ist die Datei lesbar?

Der normale Start lautet einfach:

```dos
AI4DOS
```

Du musst keinen Config-Dateinamen mit angeben. Wechsle vor dem Start in das Verzeichnis mit `AI4DOS.EXE` und `AI4DOS.CFG`: Die Datei wird aus dem aktuellen Verzeichnis geladen. Die Einträge erklärt die [DOS-Client-Konfiguration](dos-setup.md#c-dos-client-konfigurieren-ai4doscfg).

### `AI4DOS.CFG` ist ungültig

Prüfe die Datei auf:

- Tippfehler
- fehlende Werte
- ungültige IP-Adresse
- ungültigen Port
- ungültigen Device-Key
- nicht unterstützte Spracheinstellung

Vergleiche deine Datei mit dem [vollständigen CFG-Beispiel](dos-setup.md#c-dos-client-konfigurieren-ai4doscfg).

## 2. AI4DOS startet, bleibt aber OFFLINE

Wenn das Programm läuft, aber keine Verbindung zum Gateway herstellen kann, prüfe zuerst:

1. Läuft der Gateway?
2. Stimmt die IP-Adresse in `AI4DOS.CFG`?
3. Stimmt der Port?
4. Kann dein DOS-PC den Gateway-Rechner grundsätzlich erreichen?
5. Blockiert eine Firewall die Verbindung?

Bei nativen Paketen prüfe zusätzlich `host` in `server/gateway.local.json`: Der Wert bestimmt die lokalen Schnittstellen, auf denen der Gateway lauscht. `127.0.0.1` ist nur lokal erreichbar. Für das normale Heimnetz verwende `0.0.0.0` für alle IPv4-Schnittstellen. In `AI4DOS.CFG` gehört dagegen die LAN-IP des Gateway-Rechners, unter der der DOS-PC ihn erreicht.

Wenn dein Gateway im Heimnetz zum Beispiel unter:

```text
192.168.0.42
```

läuft, teste unter DOS:

```dos
PING 192.168.0.42
```

Wenn dieser Ping bereits nicht funktioniert, liegt das Problem noch **vor AI4DOS**.

→ [AI4DOS unter DOS einrichten](dos-setup.md)

## 3. Der DOS-PC erreicht den Gateway-Rechner nicht

Teste Schritt für Schritt:

```text
1. Packet Driver geladen?
        |
2. DHCP funktioniert?
        |
3. Router erreichbar?
        |
4. Gateway-Rechner erreichbar?
```

### Packet Driver prüfen

Der Packet Driver muss vor mTCP und AI4DOS geladen sein.

Wenn der Treiber beim Start bereits einen Fehler meldet, prüfe:

- I/O-Adresse
- IRQ
- Software-Interrupt
- Hardwarekonflikte

Bei PicoMEM oder einer NE2000-kompatiblen Karte müssen Hardwareeinstellung und Packet Driver zusammenpassen.

### DHCP prüfen

Starte:

```dos
DHCP
```

Wenn keine IP-Adresse bezogen wird, liegt das Problem wahrscheinlich bei:

- Packet Driver
- Netzwerkkarte
- Kabel/Verbindung
- Router/DHCP
- IRQ-/I/O-Konflikt

### Router anpingen

Zum Beispiel:

```dos
PING 192.168.0.1
```

Wenn das funktioniert, ist dein lokales DOS-Netzwerk grundsätzlich in Ordnung.

### Gateway-Rechner anpingen

Zum Beispiel:

```dos
PING 192.168.0.42
```

Wenn der Router erreichbar ist, der Gateway-Rechner aber nicht, prüfe:

- richtige IP-Adresse?
- gleicher Netzwerkbereich?
- Firewall?
- VLAN oder Gastnetz?
- läuft der Zielrechner überhaupt?

## 4. Gateway läuft, aber AI4DOS kann sich nicht authentifizieren

Wenn Netzwerk und Gateway erreichbar sind, aber die Anmeldung fehlschlägt, liegt es meistens an:

- falscher Device-ID
- falschem Device-Key

Auf DOS-Seite steht der Key in:

```text
SECRET=...
```

Auf Gateway-Seite beispielsweise:

```json
"devices": {
  "dos-pc": "..."
}
```

Beide Werte müssen **zeichenweise exakt gleich** sein.

Auch Groß-/Kleinschreibung zählt.

Prüfe außerdem, ob die Device-ID auf beiden Seiten übereinstimmt.

Für eine normale Installation verwenden wir:

```text
dos-pc
```

### Device-Key erneut setzen

Wenn du unsicher bist, wähle einen neuen Device-Key und trage ihn auf beiden Seiten neu ein.

Verwende am besten mindestens **12–16 zufällige Buchstaben und Zahlen**.

Danach Gateway und AI4DOS neu starten.

## 5. Gateway startet nicht

`Python environment is missing` bedeutet: Die projektlokale `.venv` fehlt. `Gateway dependencies are missing` bedeutet: Die benötigten Abhängigkeiten fehlen darin. Führe die Einrichtung aus der Installationsanleitung für [Windows](install-windows.md), [macOS](install-macos.md) oder [Linux](install-linux.md) durch: zuerst `.venv` anlegen, dann `server/requirements-lock.txt` darin installieren. **Das ist auch bei bereits installiertem Python nötig.** `START.BAT` und `start.sh` erledigen diese Schritte nicht automatisch. Bei Docker / Portainer ist kein Host-Python nötig.

Wenn der Gateway selbst nicht startet, prüfe zuerst:

- ist die Gateway-Konfiguration gültig?
- wurde bei nativen Paketen `.venv` eingerichtet und `server/requirements-lock.txt` darin installiert?
- wurde `<KEY>` in der Device-Konfiguration ersetzt?
- ist ein Provider ausgewählt?
- ist der API-Key eingetragen?
- wurde die Datei korrekt gespeichert?

Ein typischer Device-Eintrag sieht zum Beispiel so aus:

```json
"devices": {
  "dos-pc": "XTChat84K7M29Q"
}
```

Wenn die `devices`-Liste fehlt, leer ist oder einen ungültigen Key enthält, startet der Gateway absichtlich nicht.

## 6. API-Key funktioniert nicht

Wenn der Gateway startet, aber der KI-Anbieter den Zugang ablehnt, prüfe den API-Key.

Wichtig:

> Dein normales ChatGPT-, Claude- oder anderes Benutzerkonto ist **nicht** der API-Zugang.

Du brauchst einen separaten API-Key des jeweiligen Anbieters.

Typische Ursachen:

- API-Key falsch kopiert
- API-Key widerrufen
- API-Zugang beim Anbieter noch nicht aktiviert
- Guthaben aufgebraucht
- Abrechnung nicht eingerichtet
- falscher Anbieter ausgewählt
- API-Key gehört zu einem anderen Dienst oder Projekt

Wenn möglich, erstelle beim Anbieter einen neuen API-Key und trage ihn erneut ein.

## 7. Gateway verbindet sich mit dem Provider, aber das Modell funktioniert nicht

AI4DOS verwendet keine feste Liste erlaubter Modellnamen.

Trage bei `MODEL=` die Modell-ID exakt so ein, wie sie der jeweilige API-Anbieter bezeichnet. Den genauen Modellnamen bitte aus der API-/Developer-Dokumentation des jeweiligen Anbieters entnehmen.

Wenn du einen Modellnamen einträgst, wird er grundsätzlich an den jeweiligen Provider weitergegeben.

Fehler können deshalb bedeuten:

- Modellname falsch geschrieben
- Modell existiert nicht mehr
- Modell ist für deinen API-Zugang nicht freigeschaltet
- Modell ist in deiner Region oder deinem Tarif nicht verfügbar
- gewählte Reasoning-/Thinking-Option wird vom Modell nicht unterstützt

→ [Provider und Modelle konfigurieren](providers.md)

## 8. `REASONING` oder `THINKING` verursacht Fehler

Standardmäßig verwendet AI4DOS:

```text
REASONING=none
```

Das ist die sicherste Einstellung für den Einstieg.

Zusätzliche Reasoning-/Thinking-Modi können:

- je nach Provider anders heißen
- nicht von jedem Modell unterstützt werden
- deutlich mehr Tokens und damit höhere Kosten verursachen

Wenn nach einer Änderung Fehler auftreten:

```text
REASONING=none
```

wiederherstellen. Entferne außerdem gegebenenfalls die expliziten Overrides `REASONING_EFFORT`, `THINKING_LEVEL`, `THINKING_BUDGET`, `ENABLE_THINKING` und `CLEAR_THINKING` aus deiner aktiven Providerkonfiguration: Sie können unabhängig von `REASONING=none` weiterhin wirksam sein. Starte danach den Gateway neu.

Wenn es danach funktioniert, lag der Fehler wahrscheinlich an der gewählten Modell-/Reasoning-Kombination.

## 9. AI4DOS antwortet nicht oder bleibt lange auf TX/RX

`TX/RX` bedeutet, dass AI4DOS auf eine Antwort des Gateways bzw. Providers wartet.

Mögliche Ursachen:

- Provider reagiert langsam
- kostenloses Modell ist ausgelastet
- Provider hat aktuell eine Störung
- sehr langes Reasoning wurde aktiviert
- Netzwerkverbindung zum Gateway ist instabil

Warte zunächst kurz ab.

Wenn der Zustand regelmäßig auftritt:

- anderes Modell testen
- anderen Provider testen
- `REASONING=none` verwenden
- Gateway-Logs prüfen

AI4DOS und der Gateway besitzen Timeouts und bleiben nicht unbegrenzt in einem einzelnen Request hängen.

## 10. Antwort bricht ab

AI4DOS begrenzt Antworten bewusst, damit Speicher- und Netzwerkverbrauch auf DOS-Hardware kontrollierbar bleiben.

Wenn „Chatverlauf voll“ erscheint, nimmt der DOS-Client keine weitere Nachricht an. Speichere den bisherigen Verlauf bei Bedarf mit F5 und beginne mit F2 einen neuen Chat. Die [Antwortlimits und der Transcript-Speicher](providers.md#antwortlänge-und-transport) erklären den Unterschied zwischen Gateway-Limits und vollem DOS-Transcript. Nicht jede abgebrochene Antwort bedeutet, dass der Transcript voll ist.

Wenn eine sehr lange Antwort abgeschnitten wird und noch Platz im Transcript ist:

- Frage nach einer kürzeren Antwort
- teile eine große Aufgabe in mehrere Fragen auf
- prüfe die konfigurierte Antwortlänge auf dem Gateway

Das ist nicht zwingend ein Netzwerkfehler.

## 11. Umlaute oder Sonderzeichen sehen falsch aus

AI4DOS unterstützt DOS-Zeichensätze wie CP437 und CP850.

Prüfe:

- welche Codepage unter DOS aktiv ist
- ob AI4DOS entsprechend konfiguriert ist
- ob die verwendeten Zeichen in dieser Codepage überhaupt vorhanden sind

Deutsch mit ä, ö, ü, Ä, Ö, Ü und ß wird unterstützt.

Bei exotischen Unicode-Zeichen oder Emoji verwendet AI4DOS soweit möglich textbasierte Ersatzdarstellungen.

## 12. Das Modell fordert mich auf, eine Datei oder ein Bild hochzuladen

Der AI4DOS DOS-Client kann **grundsätzlich keine Dateien, Bilder oder sonstigen Inhalte hochladen oder bereitstellen**.

Der Gateway weist die Modelle normalerweise darauf hin.

Falls ein Modell dich trotzdem dazu auffordert, ignoriere diese Aufforderung und beschreibe den Inhalt stattdessen als Text.

Wenn dieses Verhalten regelmäßig bei einem bestimmten Provider oder Modell auftritt, melde es bitte als Fehler.

## 13. Speichern funktioniert nicht

AI4DOS speichert Chats als Textdateien.

Wenn du beim Speichern keinen Dateityp angibst, ergänzt AI4DOS automatisch:

```text
.TXT
```

Prüfe bei Fehlern:

- besteht der Dateiname aus höchstens **8 Zeichen vor dem Punkt** und höchstens **3 Zeichen für die Dateiendung**?
- ist das Zielverzeichnis vorhanden?
- ist genügend Platz auf dem Laufwerk?
- ist das Medium schreibbar?

Beispiel:

```text
CHAT1
```

wird zu:

```text
CHAT1.TXT
```

## 14. Docker-Container läuft nicht

Bei Docker Compose:

```bash
sudo docker compose ps
```

zeigt den Status.

Logs anzeigen:

```bash
sudo docker compose logs --tail=100 gateway
```

oder fortlaufend:

```bash
sudo docker compose logs -f gateway
```

Prüfe besonders:

- API-Key gesetzt?
- `gateway.json` gültig?
- Device-Key eingetragen?
- `provider.cfg` gültig?
- veröffentlichter Host-Port bereits belegt? Einen freien Host-Port wählen und `AI4DOS_PORT` sowie `PORT` in `AI4DOS.CFG` entsprechend setzen.
- Docker/Compose aktuell und funktionsfähig?

## 15. Docker läuft, aber DOS erreicht den Gateway nicht

Prüfe:

- ist der konfigurierte Host-Port veröffentlicht (gewählter Host-Port → Container `1983`)?
- stimmt die IP-Adresse des **Docker-Hosts**?
- verwendest du versehentlich die interne Container-IP?
- blockiert die Host-Firewall den veröffentlichten Host-Port?
- läuft der Container überhaupt?

Der DOS-PC verbindet sich normalerweise mit:

```text
<SERVER-IP>:<HOST-PORT>
```

Ersetze die Platzhalter durch die vom DOS-PC erreichbare Serveradresse und den gewählten Host-Port (Default `1983`). Die interne Docker-Adresse des Containers ist keine Zieladresse für den DOS-PC.

## 16. Portainer-Stack startet nicht

Öffne **Environment → Stacks → dein AI4DOS-Stack → Containers → Gateway-Container**. Dort findest du **State**, **Health**, **Logs** und **Restart**. Bei einer Restart Loop zuerst Logs und Config-Leserechte prüfen.

Prüfe in Portainer:

- Stack-Status
- Containerstatus
- Container-Logs
- Environment-Werte
- absolute Pfade zu `gateway.json` und `provider.cfg`
- Volume-/Bind-Mounts
- Portfreigabe
- ob das lokale AI4DOS-Image auf diesem Docker-Host zuvor gebaut wurde

Wenn die Stack-Datei außerhalb von AI4DOS geändert wurde, vergleiche sie mit der mitgelieferten Originalversion.

### Config-Leserechte genauer prüfen

Normalerweise reichen die Rechtebefehle aus der [Installationsanleitung](install-docker.md). Meldet der Container, dass er die Configdateien nicht lesen kann, prüfe optional genauer. Ersetze `/path/to/ai4dos` durch deinen absoluten Paketpfad:

```bash
sudo setpriv --reuid=10001 --regid=10001 --clear-groups test -r /path/to/ai4dos/config.local/gateway.json
echo $?
sudo setpriv --reuid=10001 --regid=10001 --clear-groups test -r /path/to/ai4dos/config.local/provider.cfg
echo $?
namei -l /path/to/ai4dos/config.local/gateway.json
```

`setpriv` prüft den Zugriff mit der Benutzer- und Gruppennummer des Containers. Führe jeden `test`-Befehl einzeln aus; `echo $?` direkt danach muss `0` anzeigen. `namei -l` zeigt auch die Rechte der übergeordneten Verzeichnisse. Falls die Werkzeuge auf Debian/Ubuntu fehlen, installiere `util-linux` mit `sudo apt-get install util-linux`.

Die Configdateien sollen `root:10001`, Modus `640`, das Configverzeichnis `root:10001`, Modus `750` haben. Übergeordnete Verzeichnisse müssen durchsuchbar sein; für den Paketordner reicht normalerweise Modus `755`. Keine Config-Inhalte oder Keys in Diagnoseberichte kopieren.

### Portwerte bei Compose und Portainer

Die Compose-Befehle in diesem Abschnitt verwenden die Defaults: Host-Port `1983`, Hostadresse `0.0.0.0`. Hast du andere Werte gewählt, setze sie bei jedem Aufruf wieder wie in der [Installationsanleitung](install-docker.md) beschrieben. Ohne diese Werte gelten die Defaults. Je nach Installation benötigt Docker auch für Status und Logs `sudo`.

Portainer benötigt die absoluten Hostpfade in `AI4DOS_GATEWAY_CONFIG` und `AI4DOS_PROVIDER_CONFIG`; bei anderem Host-Port zusätzlich `AI4DOS_PORT`. Das lokale Image `ai4dos-gateway:beta` muss auf derselben Docker-Umgebung vorhanden sein. Die mitgelieferte `portainer-stack.yml` gehört vollständig in den Webeditor.

Der interne Container-Listener bleibt `0.0.0.0:1983`. `AI4DOS_BIND_ADDRESS` betrifft nur die Hostadresse. Nach Portänderungen Compose `up -d` bzw. Portainer **Update the stack** verwenden; `restart` allein ändert kein Mapping.

## 17. Gateway meldet `AUTH_FAILED`

Das bedeutet:

> Der DOS-PC konnte sich nicht mit dem konfigurierten Device-Key authentifizieren.

Prüfe:

```text
DEVICE
SECRET
```

in `AI4DOS.CFG` sowie den passenden Eintrag unter:

```json
"devices"
```

im Gateway.

Der Gateway beendet die Verbindung nach einer fehlgeschlagenen Authentifizierung absichtlich.

## 18. Viele `AUTH_FAILED`-Meldungen im Serverlog

Der Gateway protokolliert fehlgeschlagene Authentifizierungen beispielsweise als:

```text
AUTH_FAILED peer=203.0.113.10 device=dos-pc
```

Wenn du einen öffentlich erreichbaren VPS oder Dedicated Server verwendest, können automatisierte Scanner solche Versuche verursachen.

AI4DOS enthält bewusst kein eigenes Ban-System.

Serveradministratoren können solche Logeinträge beispielsweise mit Fail2Ban auswerten.

Allgemeine Serverabsicherung bleibt Aufgabe des Host-Administrators.

## 19. Gateway-Port ist vom Internet erreichbar

Wenn du AI4DOS auf einem VPS oder Dedicated Server betreibst und dein DOS-PC den Gateway direkt über das Internet erreichen soll, muss der verwendete TCP-Port öffentlich erreichbar sein (Docker: veröffentlichter Host-Port, z. B. `1983`; nativ: Listener-Port, standardmäßig `1983`).

In diesem Fall solltest du wie bei jedem anderen Netzwerkdienst auf eine vernünftig administrierte Umgebung achten:

- aktuelle Software
- Firewall
- nur benötigte Ports
- starke Device-Keys
- gegebenenfalls Fail2Ban

Wenn du nicht möchtest, dass der verwendete Gateway-Port öffentlich erreichbar ist, empfehlen wir die Verwendung einer VPN-Verbindung.

## 20. Erst lief alles, jetzt plötzlich nicht mehr

Prüfe, was sich zuletzt geändert hat:

- neue IP-Adresse des Gateway-Rechners?
- Router neu gestartet?
- DHCP hat andere Adresse vergeben?
- API-Key geändert oder abgelaufen?
- anderes Modell eingestellt?
- Provider aktuell gestört?
- Firewall geändert?
- Device-Key verändert?
- Packet Driver nach DOS-Neustart nicht geladen?

Bei lokalen Gateways ist eine geänderte IP-Adresse nach einem Router-/PC-Neustart eine besonders häufige Ursache.

## 21. Fehler sinnvoll eingrenzen

Wenn du nicht weißt, wo du anfangen sollst:

```text
AI4DOS.EXE startet?
        |
        v
DOS-Netzwerk funktioniert?
        |
        v
Gateway-Rechner pingbar?
        |
        v
Gateway läuft?
        |
        v
Device-Key stimmt?
        |
        v
Provider/API-Key funktioniert?
        |
        v
Modell verfügbar?
```

Teste immer nur **eine Ebene nach der anderen**.

## Noch immer festgefahren?

Wenn unsere Anleitung an einer Stelle unklar ist, sag uns bitte Bescheid.

**Wenn du dort hängenbleibst, wird vermutlich auch der nächste Nutzer darüber stolpern. Dann sollten wir die Anleitung verbessern.**

Für eine Support-Anfrage helfen besonders:

- welches DOS und welche Hardware du verwendest
- welche Netzwerklösung du verwendest
- ob mTCP/Ping funktioniert
- welche Gateway-Plattform du verwendest
- genaue Fehlermeldung
- was unmittelbar davor funktioniert hat

**Bitte niemals API-Keys oder Device-Keys öffentlich posten.**
