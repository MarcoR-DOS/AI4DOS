# AI4DOS Gateway unter Windows einrichten

Diese Anleitung richtet den AI4DOS Gateway auf einem Windows-PC oder Notebook ein.

Am Ende läuft der Gateway auf deinem Windows-Rechner und dein DOS-PC kann sich mit ihm verbinden.

## Was du brauchst

Bevor du anfängst, brauchst du:

- das **AI4DOS Server-Paket für Windows**
- **Python 3.9 oder neuer**, über die Kommandozeile erreichbar
- einen API-Key für einen unterstützten KI-Anbieter
- deinen DOS-PC im selben Netzwerk
- einen selbst gewählten Device-Key

Falls du noch keinen API-Zugang eingerichtet hast, lies zuerst:

→ [KI-Anbieter und API-Zugang einrichten](providers.md)

## 1. Serverpaket entpacken

Lade das passende Paket von der [AI4DOS GitHub-Releases-Seite](https://github.com/MarcoR-DOS/AI4DOS/releases) herunter.

Entpacke das Windows-Serverpaket in einen Ordner deiner Wahl.

Zum Beispiel:

```text
C:\AI4DOS
```

AI4DOS muss nicht installiert werden. Der Gateway läuft direkt aus diesem Ordner.

## 2. Python und Abhängigkeiten vorbereiten

Für jedes frisch entpackte native AI4DOS-Paket sind **zwei getrennte Voraussetzungen** nötig:

- **A: Python 3.9 oder neuer** muss auf dem Rechner installiert sein.
- **B: Eine projektlokale Python-Umgebung `.venv`** muss einmalig im entpackten Paketordner angelegt und mit den AI4DOS-Abhängigkeiten aus `server/requirements-lock.txt` befüllt werden.

### A. Python-Version prüfen

Prüfe in einer Eingabeaufforderung:

```bat
py -3 --version
```

Falls Python 3.9 oder neuer noch nicht vorhanden ist, installiere eine passende Version mit dem Python-Launcher `py`.

### B. AI4DOS-Umgebung immer einrichten

**Diesen Schritt musst du auch durchführen, wenn Python bereits installiert ist und die Versionsprüfung erfolgreich war.** Die Versionsprüfung ersetzt die Einrichtung nicht.

Wechsle in den entpackten AI4DOS-Paketordner und führe einmalig aus:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r server\requirements-lock.txt
```

Damit wird `.venv` im Paketordner angelegt und mit den benötigten Abhängigkeiten ausgestattet. `START.BAT` legt diese Umgebung **nicht automatisch an** und installiert **keine Abhängigkeiten automatisch**. Erst nach beiden Schritten kannst du den Gateway starten.

## 3. KI-Anbieter eintragen

Öffne `server/provider.local.cfg` mit einem normalen Texteditor. Trage deinen API-Key bei `API_KEY=` ein.

Dort legst du fest:

- welchen KI-Anbieter du verwenden möchtest
- welchen API-Key AI4DOS dafür verwenden soll
- welches Modell verwendet werden soll

Für den ersten Test kannst du die im Paket vorbereiteten Standardwerte verwenden und nur deinen API-Key eintragen.

AI4DOS pflegt keine feste Modellliste. Trage bei `MODEL=` die Modell-ID exakt so ein, wie sie der jeweilige API-Anbieter bezeichnet. Den genauen Modellnamen bitte aus der API-/Developer-Dokumentation des jeweiligen Anbieters entnehmen.

Für den einfachen kostenlosen Einstieg mit OpenRouter kannst du den vorbereiteten Standardwert `MODEL=openrouter/free` zunächst unverändert lassen. OpenRouter kann dann ein aktuell verfügbares kostenloses Modell auswählen. Wenn du später ein bestimmtes Modell nutzen möchtest, trägst du dessen Modell-ID bei `MODEL=` ein.

Andere Anbieter und Modelle kannst du später jederzeit einstellen.

Gültige Werte für `PROVIDER=`: `openai`, `anthropic`, `gemini`, `mistral`, `nvidia`, `openrouter`, `openai-compatible`.

→ [Provider und Modelle konfigurieren](providers.md)

## 4. Device-Key eintragen

Öffne anschließend `server/gateway.local.json`.

`host` in der Gateway-Konfiguration bestimmt, auf welchen lokalen Schnittstellen der Gateway lauscht. Die Vorlage enthält `"host": "127.0.0.1"` und ist damit nur auf dem Gateway-Rechner selbst erreichbar. Für den normalen Heimnetz-Fall setze `"host": "0.0.0.0"`, damit der Gateway auf allen IPv4-Schnittstellen lauscht. Ermittle danach die LAN-IP des Gateway-Rechners und trage genau diese Adresse später in `AI4DOS.CFG` ein: Sie ist die Adresse, unter der dein DOS-PC den Gateway erreicht. `0.0.0.0` ist keine Zieladresse für den DOS-PC; die LAN-IP des DOS-PCs gehört nicht in `host`. Der Standardport bleibt `1983`; er muss in der Firewall erreichbar sein.

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

Diesen Key brauchst du gleich noch einmal auf deinem DOS-PC.

Wichtig: Der Wert muss auf beiden Seiten **exakt gleich** sein.

## 5. Gateway starten

Starte `START.BAT`.

Der Gateway sollte nun seine Konfiguration laden und auf Verbindungen warten.

Wenn beim Start ein Fehler erscheint, prüfe zunächst:

- ist der API-Key eingetragen?
- ist ein gültiger Device-Key eingetragen?
- wurde die Konfigurationsdatei korrekt gespeichert?

Falls der Gateway sauber startet, kannst du ihn zunächst geöffnet lassen.

## 6. Windows-Firewall

Beim ersten Start fragt Windows möglicherweise, ob der Gateway Netzwerkzugriff erhalten darf.

Erlaube den Zugriff für dein **privates Netzwerk**.

Für einen normalen Rechner zuhause musst du den AI4DOS-Port nicht im Router ins Internet weiterleiten.

Der DOS-PC muss den Windows-Rechner lediglich innerhalb deines lokalen Netzwerks erreichen können.

## 7. IP-Adresse des Windows-Rechners herausfinden

Dein DOS-PC muss wissen, unter welcher Adresse er den Gateway erreichen kann.

Öffne unter Windows eine Eingabeaufforderung und gib ein:

```bat
ipconfig
```

Suche bei deiner aktiven Netzwerkverbindung nach der **IPv4-Adresse**.

Zum Beispiel:

```text
192.168.0.42
```

Diese Adresse brauchst du gleich für `AI4DOS.CFG`.

Hinweis: `127.0.0.1` funktioniert hier nicht. Diese Adresse bedeutet immer „dieser Rechner selbst“. Auf deinem DOS-PC würde sie also auf den DOS-PC zeigen und nicht auf den Windows-Rechner.

## 8. DOS-Konfiguration eintragen

Öffne die mitgelieferte:

```text
AI4DOS.CFG
```

und trage dort:

- die IP-Adresse deines Windows-Rechners
- denselben Device-Key wie im Gateway
- deine gewünschte Sprache

ein.

Die Datei enthält bereits die passenden Einträge und Hinweise.

Danach kopierst du `AI4DOS.EXE` und `AI4DOS.CFG` auf deinen DOS-PC.

## 9. Verbindung testen

Stelle sicher, dass dein DOS-PC bereits eine funktionierende Netzwerkverbindung hat.

Wenn dein DOS-PC mit mTCP schon andere Rechner in deinem Netzwerk erreichen kann, ist das normalerweise ausreichend.

Falls nicht:

→ [AI4DOS unter DOS einrichten](dos-setup.md)

## 10. AI4DOS starten

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

## Wenn keine Verbindung zustande kommt

Prüfe zuerst diese Punkte:

- Läuft der AI4DOS Gateway auf dem Windows-Rechner?
- Stimmt die IP-Adresse in `AI4DOS.CFG`?
- Ist der Device-Key auf beiden Seiten exakt gleich?
- Hat Windows den Netzwerkzugriff für den Gateway erlaubt?
- Kann dein DOS-PC den Windows-Rechner grundsätzlich im Netzwerk erreichen?

Weitere Hilfe:

→ [Fehlerbehebung](troubleshooting.md)

## Später ändern

Wenn AI4DOS läuft, kannst du später problemlos:

- einen anderen KI-Anbieter verwenden
- ein anderes Modell auswählen
- einen anderen Device-Key setzen
- den Gateway auf einen anderen Rechner verschieben

Speichere Änderungen in `server/gateway.local.json` bzw. `server/provider.local.cfg`, beende den laufenden Gateway mit **Strg+C** und starte ihn wie in Abschnitt 5 erneut. Bei geändertem Listener-Port setze auch `PORT` in `AI4DOS.CFG` entsprechend und starte den DOS-Client neu. Bereits gespeicherte Chatdateien bleiben erhalten.

→ [DOS-Client-Konfiguration](dos-setup.md#c-dos-client-konfigurieren-ai4doscfg) · [Provider und Modelle](providers.md)

Für einen Test ohne API-Zugang siehe [Offline-Funktionstest](providers.md#offline-funktionstest-ohne-api-zugang). Bei einem abweichenden Listener-Port muss auch die Firewallfreigabe diesen Port verwenden.
