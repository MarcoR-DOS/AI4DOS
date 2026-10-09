# AI4DOS Quick Start

**AI4DOS ist ein Chat-Client für MS-DOS, mit dem du ChatGPT, Claude, Google Gemini, Mistral und andere KI-Dienste direkt auf deinem DOS-PC nutzen kannst.**

AI4DOS wurde unter anderem auf einem echten IBM PC XT mit 4,77 MHz und 512 KB RAM getestet. Für den Betrieb benötigt das Programm mindestens **256 KB freien konventionellen Speicher**.

## Was du dafür brauchst

AI4DOS besteht aus zwei Teilen:

- dem **DOS-Client** auf deinem DOS-PC
- dem **AI4DOS Gateway** auf einem modernen Rechner

Der Gateway ist eine Art technischer Mittelsmann zwischen deinem DOS-PC und dem KI-Dienst.

Moderne KI-Dienste verwenden aktuelle HTTPS-/TLS-Verbindungen, Zertifikate und Web-APIs, mit denen ein klassischer DOS-PC nicht ohne Weiteres direkt kommunizieren kann. Der Gateway übernimmt deshalb diesen modernen Teil und übersetzt zwischen beiden Seiten.

```text
DOS-PC  <-->  AI4DOS Gateway  <-->  KI-Dienst
```

Du kannst dir das ein bisschen wie einen Dolmetscher zwischen zwei sehr unterschiedlichen Computersprachen vorstellen.

Der Gateway kann zum Beispiel auf einem Windows-PC, Mac, Linux-Rechner, Raspberry Pi, NAS, Homeserver oder VPS laufen.

## 1. Lade die passenden Pakete herunter

Du brauchst immer das **DOS-Paket**.

Dazu lädst du genau das **Serverpaket** herunter, das zu deinem modernen Rechner bzw. deiner Serverumgebung passt:

- Windows
- macOS
- Linux
- Docker

Die Pakete werden getrennt angeboten. Du musst also nicht ein großes Gesamtpaket herunterladen, das Dateien für alle Plattformen enthält.

## 2. Wähle deinen KI-Anbieter

Für AI4DOS brauchst du einen Zugang zu einem unterstützten KI-Dienst, zum Beispiel:

- OpenAI / ChatGPT
- Anthropic / Claude
- Google Gemini
- Mistral
- NVIDIA
- OpenRouter

Wichtig: Deine normalen Zugangsdaten zu ChatGPT, Claude oder einem anderen Abo kannst du hier **nicht** verwenden, da diese nur mit den offiziellen Zugangswegen des jeweiligen Anbieters funktionieren – zum Beispiel im Webbrowser oder in dessen Mobile-/Desktop-Apps.

AI4DOS verbindet sich daher über einen sogenannten **API-Zugang** mit dem KI-Dienst. Diese Schnittstellen sind speziell dafür gedacht, dass auch Software von Drittanbietern mit dem jeweiligen KI-Dienst kommunizieren kann. Dafür erhältst du einen separaten API-Key.

Für den einfachsten Einstieg empfehlen wir **OpenRouter**.

OpenRouter ist kein Netzwerk-Router, sondern ein Dienst, über den du mit einem einzigen API-Zugang verschiedene KI-Modelle nutzen kannst.

Damit kannst du AI4DOS zunächst mit einem kostenlosen Modell ausprobieren. Alternativ kannst du direkt einen API-Zugang bei einem anderen unterstützten Anbieter deiner Wahl verwenden.

Gültige Werte für `PROVIDER=`: `openai`, `anthropic`, `gemini`, `mistral`, `nvidia`, `openrouter`, `openai-compatible`.

AI4DOS pflegt keine feste Modellliste. Trage bei `MODEL=` die Modell-ID exakt so ein, wie sie der jeweilige API-Anbieter bezeichnet. Den genauen Modellnamen bitte aus der API-/Developer-Dokumentation des jeweiligen Anbieters entnehmen.

Für den einfachen kostenlosen Einstieg mit OpenRouter kannst du den vorbereiteten Standardwert `MODEL=openrouter/free` zunächst unverändert lassen. OpenRouter kann dann ein aktuell verfügbares kostenloses Modell auswählen. Wenn du später ein bestimmtes Modell nutzen möchtest, trägst du dessen Modell-ID bei `MODEL=` ein.

→ [Provider und Modelle konfigurieren](providers.md)

## 3. Richte den Gateway ein

Entpacke das passende Serverpaket und folge der Installationsanleitung für deine Plattform:

- [Windows einrichten](install-windows.md)
- [macOS einrichten](install-macos.md)
- [Linux einrichten](install-linux.md)
- [Docker / Portainer einrichten](install-docker.md)

**Windows, macOS und Linux:** Für das Gateway benötigst du Python 3.9 oder neuer. Die Einrichtung wird in der jeweiligen Installationsanleitung Schritt für Schritt erklärt: [Windows](install-windows.md), [macOS](install-macos.md), [Linux](install-linux.md).

**Docker / Portainer:** Python muss auf dem Host nicht installiert werden.

Bei der Einrichtung trägst du deinen API-Key ein.

Außerdem benötigt AI4DOS einen **Device-Key**. Dieser authentifiziert deinen DOS-PC gegenüber deinem AI4DOS Gateway. Die Chatdaten werden dadurch nicht verschlüsselt.

Den Device-Key wählst du selbst. Verwende dafür am besten mindestens **12–16 zufällige Buchstaben und Zahlen**, gerne mehr, und keinen Schlüssel, den du bereits anderswo benutzt.

Denselben Device-Key trägst du später sowohl in der Gateway-Konfiguration als auch in `AI4DOS.CFG` auf deinem DOS-PC ein.

Mehr musst du darüber für den Einstieg nicht wissen:

- der **API-Key** gehört zum KI-Anbieter
- der **Device-Key** gehört zu deinem eigenen AI4DOS-Gateway

## 4. Richte AI4DOS auf dem DOS-PC ein

Entpacke das DOS-Paket.

Darin befinden sich unter anderem:

```text
AI4DOS.EXE
AI4DOS.CFG
```

Öffne `AI4DOS.CFG` mit einem normalen Texteditor.

In diese Konfigurationsdatei kommt:

- die IP-Adresse deines Gateway-Rechners
- der Device-Key
- die Sprache, in der du AI4DOS verwenden möchtest

Das musst du dir aber nicht merken. Die Datei liegt bereits als Vorlage bei und erklärt die einzelnen Einträge.

Kopiere anschließend `AI4DOS.EXE` und `AI4DOS.CFG` auf deinen DOS-PC.

## 5. Prüfe das DOS-Netzwerk

Damit AI4DOS mit dem Gateway sprechen kann, muss dein DOS-PC bereits eine funktionierende Netzwerkverbindung haben.

Wenn dein DOS-PC schon mit mTCP ins Netzwerk kommt, kannst du direkt weitermachen.

Falls Netzwerk unter DOS für dich noch neu ist:

→ [AI4DOS unter DOS einrichten](dos-setup.md)

Dort zeigen wir dir Schritt für Schritt, was du dafür brauchst.

## 6. Starte AI4DOS

Wechsle auf deinem DOS-PC in das Verzeichnis mit AI4DOS und starte:

```dos
AI4DOS
```

Mehr ist nicht nötig.

`AI4DOS.EXE` lädt automatisch die danebenliegende:

```text
AI4DOS.CFG
```

Wenn die Verbindung funktioniert, erscheint oben rechts:

```text
ONLINE
```

Jetzt kannst du deine erste Nachricht eingeben und mit **Enter** abschicken.

## Fertig

Du chattest jetzt von deinem DOS-PC aus mit einem modernen KI-Dienst.

## Wenn etwas nicht funktioniert

Besonders bei echten DOS-Rechnern unterscheiden sich Netzwerkkarten, Packet Driver und vorhandene Netzwerkkonfigurationen teilweise erheblich.

Die häufigsten Probleme findest du hier:

→ [Fehlerbehebung](troubleshooting.md)

Falls du an einer Stelle hängenbleibst, weil unsere Anleitung unklar ist, sag uns bitte Bescheid.

**Wenn du dort hängenbleibst, wird vermutlich auch der nächste Nutzer darüber stolpern. Dann sollten wir die Anleitung verbessern.**

## Was du später noch ändern kannst

Wenn der erste Test läuft, kannst du unter anderem:

- einen anderen KI-Anbieter verwenden
- ein bestimmtes Modell auswählen
- Sprache und weitere Optionen anpassen
- den Gateway auf einen anderen Rechner oder Server verschieben

Details findest du bei der [DOS-Client-Konfiguration](dos-setup.md#c-dos-client-konfigurieren-ai4doscfg), unter [Provider und Modelle](providers.md) und in der jeweiligen Plattformanleitung aus Abschnitt 3.

Paketdateien:

| Plattform | ZIP |
| --- | --- |
| DOS | `AI4DOS-DOS.zip` |
| Windows | `AI4DOS-Server-Windows.zip` |
| macOS | `AI4DOS-Server-macOS.zip` |
| Linux | `AI4DOS-Server-Linux.zip` |
| Docker / Portainer | `AI4DOS-Server-Docker.zip` |
