# AI4DOS Gateway mit Docker / Portainer einrichten

Diese Anleitung richtet den AI4DOS Gateway in einer Docker-Umgebung ein.

Das kann zum Beispiel ein NAS, Raspberry Pi, Homeserver, Linux-Server oder VPS sein. Du kannst AI4DOS entweder direkt mit **Docker Compose** oder über **Portainer** betreiben.

Am Ende läuft der Gateway in einem Container und dein DOS-PC kann sich mit ihm verbinden.

## 1. Was du brauchst

Bevor du anfängst, brauchst du:

- das **AI4DOS Server-Paket für Docker**
- eine funktionierende Docker-Umgebung mit Docker Compose
- Shell-/SSH-Zugang zum Docker-Host, auch wenn du Portainer verwendest
- einen API-Key für einen unterstützten KI-Anbieter
- deinen DOS-PC mit einer Netzwerkverbindung zum Docker-Host
- einen selbst gewählten Device-Key

**Für Portainer reicht die Weboberfläche allein nicht.** Du brauchst zusätzlich Zugang zur Shell auf dem Docker-Host: Dort entpackst du das ZIP, bereitest die Configdateien vor und baust einmal das lokale Image.

Für Docker und Portainer ist **kein Python auf dem Host nötig**. Python und die benötigten Abhängigkeiten sind im Container/Image enthalten.

Falls du noch keinen API-Zugang eingerichtet hast, lies zuerst:

→ [KI-Anbieter und API-Zugang einrichten](providers.md)

## 2. Docker-Paket entpacken

Lade das passende Paket von der [AI4DOS GitHub-Releases-Seite](https://github.com/MarcoR-DOS/AI4DOS/releases) herunter.

Entpacke das Docker-Serverpaket auf dem Rechner oder Server, auf dem der Gateway laufen soll.

Die DOS-Dateien gehören **nicht** in diesen Ordner. Sie werden separat auf deinem DOS-PC verwendet.

Im Docker-Paket findest du die Dateien, die für den Gateway und den Container benötigt werden.

Ersetze `/path/to/ai4dos` in den folgenden Befehlen durch den absoluten Pfad deines entpackten Paketordners. Zum Entpacken benötigt der Linux-Host `unzip`. Falls es auf Debian/Ubuntu fehlt, installiere es zuerst:

```bash
sudo apt-get update
sudo apt-get install unzip
```

Zum Beispiel auf einem Linux-Host:

```bash
sudo mkdir -p /path/to/ai4dos
sudo unzip AI4DOS-Server-Docker.zip -d /path/to/ai4dos
cd /path/to/ai4dos
```

## 3. KI-Anbieter einrichten

Öffne auf dem Docker-Host `config.local/provider.cfg`, zum Beispiel mit:

```bash
sudoedit config.local/provider.cfg
```

Dort legst du fest:

- welchen KI-Anbieter du verwenden möchtest
- welches Modell verwendet werden soll
- welche weiteren Provideroptionen du verwenden möchtest

Trage den API-Key in derselben Datei bei `API_KEY=` ein. Provider, API-Key, Modell und optionale Providerwerte stehen gemeinsam in `config.local/provider.cfg`.

Für den ersten Test kannst du die vorbereiteten Standardwerte verwenden und nur deinen API-Key ergänzen.

AI4DOS pflegt keine feste Modellliste. Trage bei `MODEL=` die Modell-ID exakt so ein, wie sie der jeweilige API-Anbieter bezeichnet. Den genauen Modellnamen bitte aus der API-/Developer-Dokumentation des jeweiligen Anbieters entnehmen.

Für den einfachen kostenlosen Einstieg mit OpenRouter kannst du den vorbereiteten Standardwert `MODEL=openrouter/free` zunächst unverändert lassen. OpenRouter kann dann ein aktuell verfügbares kostenloses Modell auswählen. Wenn du später ein bestimmtes Modell nutzen möchtest, trägst du dessen Modell-ID bei `MODEL=` ein.

Gültige Werte für `PROVIDER=`: `openai`, `anthropic`, `gemini`, `mistral`, `nvidia`, `openrouter`, `openai-compatible`.

→ [Provider und Modelle konfigurieren](providers.md)

## 4. Device-Key eintragen

Öffne auf dem Docker-Host:

```bash
sudoedit config.local/gateway.json
```

Dort findest du den Bereich:

```json
"devices": {
  "dos-pc": "<KEY>"
}
```

Ersetze `<KEY>` durch einen selbst gewählten Device-Key.

Verwende am besten mindestens **12–16 zufällige Buchstaben und Zahlen**, gerne mehr.

Zum Beispiel:

```json
"devices": {
  "dos-pc": "XTChat84K7M29Q"
}
```

Diesen Key brauchst du später noch einmal in `AI4DOS.CFG` auf deinem DOS-PC.

Der Wert muss auf beiden Seiten **exakt gleich** sein.

### Configdateien schützen

Der Container liest die Configs als Benutzer und Gruppe `10001:10001`. Führe nach dem Bearbeiten im Paketordner aus:

```bash
sudo chown root:10001 config.local config.local/gateway.json config.local/provider.cfg
sudo chmod 750 config.local
sudo chmod 640 config.local/gateway.json config.local/provider.cfg
```

Damit bleiben die Dateien geschützt und für den Container lesbar. Verwende kein `chmod 777`. Zum späteren Bearbeiten nutze weiterhin `sudoedit`.

## 5. Wähle deinen Installationsweg

**Wähle genau einen Weg: Docker Compose oder Portainer. Du musst nicht beide durchführen.** Danach geht es mit Abschnitt 6 weiter.

Beide Wege verwenden standardmäßig Host-Port `1983`. Im Container ist der Listener bereits fest auf `0.0.0.0:1983` eingestellt; ändere dafür weder `host` noch `port` in `gateway.json`.

Die Shellbefehle verwenden `sudo`, weil Docker je nach Installation erhöhte Rechte benötigt. Das gilt auch für Status und Logs. Hat dein Benutzer bereits Docker-Zugriff, kannst du `sudo` weglassen.

### Variante A: Docker Compose

Führe im entpackten Paketordner aus:

```bash
sudo docker compose build
sudo docker compose up -d
sudo docker compose ps
```

Der erste Befehl baut das lokale Image; dabei lädt Docker gegebenenfalls das Basisimage und Abhängigkeiten. Der zweite startet den Gateway im Hintergrund. Der dritte zeigt, ob der Container läuft und als `healthy` gilt. Wird noch `starting` angezeigt, warte kurz und prüfe erneut.

#### Nur bei einem anderen Host-Port oder einer anderen Hostadresse

Ist Host-Port `1983` bereits belegt, wähle einen freien Port. Ersetze `<HOST-PORT>` durch dessen Nummer:

```bash
sudo env AI4DOS_PORT=<HOST-PORT> docker compose up -d
sudo env AI4DOS_PORT=<HOST-PORT> docker compose ps
```

Der interne Container-Port bleibt `1983`. Verwende den gewählten Host-Port später auch in `AI4DOS.CFG` und in der Host-Firewall.

Standardmäßig veröffentlicht Docker auf allen IPv4-Schnittstellen des Hosts (`0.0.0.0`). Soll der Port nur an einer bestimmten Hostadresse erreichbar sein, ergänze beim Start `AI4DOS_BIND_ADDRESS=<HOST-IP>` direkt hinter `env`. Diese Variable betrifft den Host, nicht den Container.

**Verwende gewählte Abweichungen bei allen späteren Compose-Aufrufen wieder**, auch in einer neuen SSH-Sitzung: `sudo env AI4DOS_PORT=<HOST-PORT> docker compose ...`; bei geänderter Hostadresse zusätzlich `AI4DOS_BIND_ADDRESS=<HOST-IP>`. Ohne diese Werte gelten wieder die Defaults. Eine `.env` ist nicht nötig. Für `build` allein sind diese Variablen nicht erforderlich.

### Variante B: Portainer

Wähle in Portainer eine **Docker Standalone**-Umgebung auf demselben Host, auf dem du das Paket entpackt und die Configs vorbereitet hast.

Baue zuerst in der Shell dieses Hosts, im Paketordner, das lokale Image:

```bash
sudo docker compose build
cat portainer-stack.yml
```

Der Build erzeugt `ai4dos-gateway:beta` und startet keinen Container. `cat` zeigt den mitgelieferten Stackinhalt zum Kopieren.

In Portainer:

1. Öffne die passende **Environment → Stacks → Add stack** und gib einen Namen ein, zum Beispiel `ai4dos`.
2. Wähle **Web editor** und füge den vollständigen Inhalt von **`portainer-stack.yml`** ein. Alternativ verwende **Upload** mit genau dieser Datei. **`docker-compose.yml` ist nicht die Portainer-Stackdatei.**
3. Unter dem Editor bei **Environment variables → Add an environment variable** trägst du die folgenden Werte ein. Ersetze `/path/to/ai4dos` durch den absoluten Paketpfad auf dem Docker-Host:

| Name | Wert | Benötigt? |
| --- | --- | --- |
| `AI4DOS_GATEWAY_CONFIG` | `/path/to/ai4dos/config.local/gateway.json` | ja |
| `AI4DOS_PROVIDER_CONFIG` | `/path/to/ai4dos/config.local/provider.cfg` | ja |
| `AI4DOS_PORT` | `<HOST-PORT>` | nur bei anderem Host-Port als `1983` |
| `AI4DOS_BIND_ADDRESS` | `<HOST-IP>` | nur bei anderer Hostadresse als `0.0.0.0` |

4. Die Pfade beziehen sich auf den **Docker-Host**, nicht auf deinen Browserrechner. Beide Dateien müssen dort bereits existieren. **Keine API- oder Device-Keys in Portainer-Variablen eintragen**; sie bleiben in den Configdateien.
5. Klicke **Deploy the stack**. Die Stackdatei verwendet das lokal gebaute Image; aktiviere keinen erneuten Image-Pull aus einer Registry.
6. Öffne **Stacks → dein Stack → Containers → Gateway-Container**. Unter **State** und **Health** sollte er laufen und `healthy` sein. Unter **Logs** findest du die Gateway-Ausgaben.

## 6. Netzwerk und DOS-Konfiguration

Der DOS-PC verbindet sich mit der **Host-IP und dem veröffentlichten Host-Port**. Ersetze die Platzhalter durch deine Serveradresse und den gewählten Host-Port (Default `1983`):

```ini
SERVER=<SERVER-IP>
PORT=<HOST-PORT>
DEVICE=dos-pc
SECRET=<dein Device-Key>
```

Diese Werte stehen in `AI4DOS.CFG` aus dem separaten DOS-Paket. Der Device-Key muss exakt dem Wert in `gateway.json` entsprechen. Die interne Container-IP und `0.0.0.0` sind keine DOS-Zieladressen; `127.0.0.1` würde auf den DOS-PC selbst zeigen.

Die Host-Firewall bzw. ein VPN muss den **veröffentlichten Host-Port** vom DOS-PC aus erreichbar machen, standardmäßig TCP `1983`. Im Heimnetz ist normalerweise keine Internet-Router-Portweiterleitung nötig. Pflege Betriebssystem und Docker wie gewohnt. Die HMAC-Authentifizierung verschlüsselt den DOS-Verkehr nicht; für vertrauliche Verbindungen nutze ein geeignetes geschütztes Netzwerk/VPN.

## 7. Verbindung testen / AI4DOS starten

Stelle sicher, dass dein DOS-PC bereits eine funktionierende Netzwerkverbindung hat.

Wenn dein DOS-PC mit mTCP den Docker-Host oder Server erreichen kann, ist das normalerweise ausreichend.

Falls nicht:

→ [AI4DOS unter DOS einrichten](dos-setup.md)

Auf dem DOS-PC:

```dos
AI4DOS
```

AI4DOS lädt automatisch `AI4DOS.CFG` und versucht, den Gateway zu erreichen.

Wenn alles funktioniert, erscheint oben rechts:

```text
ONLINE
```

Jetzt kannst du deine erste Nachricht eingeben und mit **Enter** abschicken.

## 8. Wenn keine Verbindung zustande kommt

Prüfe zuerst:

- Läuft der Container?
- Ist der Gateway im Container erfolgreich gestartet?
- Stimmt die Adresse in `AI4DOS.CFG`?
- Ist der Device-Key auf beiden Seiten exakt gleich?
- Ist der veröffentlichte Host-Port (standardmäßig TCP `1983`) vom DOS-PC aus erreichbar?
- Ist der API-Key korrekt eingetragen?
- Läuft auf dem Server eine Firewall, die den Port blockiert?

Für Docker Compose: Führe im entpackten Paketordner aus:

```bash
sudo docker compose ps
```

Das zeigt, ob der Gateway-Container läuft und ob er als `healthy` gilt.

```bash
sudo docker compose logs --tail=100 gateway
```

Das zeigt die letzten 100 Gateway-Logzeilen. Dort findest du normalerweise die eigentliche Start- oder Konfigurationsfehlermeldung.

Verwendest du einen anderen Host-Port oder eine andere Hostadresse, setze die Werte bei diesen Aufrufen wie in Variante A beschrieben erneut.

Bei Portainer öffne den Gateway-Container im Stack und prüfe **State**, **Health** und **Logs**. Bei einer Restart Loop prüfe zuerst die Fehlermeldung, die Configpfade und die Leserechte. Eine genauere Rechteprüfung findest du in der [Fehlerbehebung](troubleshooting.md#config-leserechte-genauer-prüfen).

Weitere Hilfe:

→ [Fehlerbehebung](troubleshooting.md)

## 9. Später ändern

Wenn AI4DOS läuft, kannst du später problemlos:

- einen anderen KI-Anbieter verwenden
- ein anderes Modell auswählen
- einen anderen Device-Key setzen
- den Container auf einen anderen Docker-Host verschieben
- zwischen Docker Compose und Portainer wechseln

Für Docker Compose: Bearbeite die Configdateien mit `sudoedit` und starte den Gateway neu:

```bash
sudo docker compose restart gateway
```

Um laufende Gateway-Ausgaben zu verfolgen, verwende `sudo docker compose logs -f gateway`. Bei geändertem Host-Port oder geänderter Hostadresse setze jeweils wieder die in Variante A beschriebenen Werte. Änderungen am Portmapping benötigen `up -d`; `restart` allein ändert kein Mapping.

Bei Portainer lädt **Restart** im Gateway-Container bearbeitete Configs neu. Bei Portänderungen verwende **Update the stack**.

Wenn du von Compose zu Portainer wechselst oder Compose beenden möchtest:

```bash
sudo docker compose down
```

Setze auch hier gegebenenfalls die abweichenden Hostwerte. Beide Installationswege dürfen nicht gleichzeitig denselben Host-Port verwenden. Einen eigenen Portainer-Stack entfernst du über **Delete this stack / Remove** in dessen Stackdetails.

→ [DOS-Client-Konfiguration](dos-setup.md#c-dos-client-konfigurieren-ai4doscfg) · [Provider und Modelle](providers.md)
