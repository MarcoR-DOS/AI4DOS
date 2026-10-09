# Provider und Modelle konfigurieren

## 1. API-Zugang einrichten

Du brauchst einen separaten API-Zugang und einen API-Key beim gewählten Anbieter. Ein normales ChatGPT-, Claude- oder Gemini-Abo ist **kein API-Zugang**; die Anmeldung in der Website oder App genügt nicht.

Für den einfachen Einstieg empfehlen wir **OpenRouter**. Der Dienst bietet mit einem API-Zugang Zugriff auf verschiedene Modelle, darunter kostenlose Angebote. Die Vorlage verwendet `PROVIDER=openrouter` und `MODEL=openrouter/free`. Lege einen OpenRouter-API-Key an und trage ihn auf dem Gateway ein. Welche kostenlosen Modelle und Kontingente verfügbar sind, bestimmt OpenRouter; diese Anleitung führt keine feste Modellliste.

## 2. Provider auf dem Gateway eintragen

Öffne die Providerdatei mit einem normalen Texteditor:

- Windows, macOS und Linux: `server/provider.local.cfg`
- Docker / Portainer: `config.local/provider.cfg`

Wähle einen Anbieter und übernimm den Wert genau:

| Anbieter | Wert für `PROVIDER=` |
| --- | --- |
| OpenAI / ChatGPT | `openai` |
| Anthropic / Claude | `anthropic` |
| Google Gemini | `gemini` |
| Mistral | `mistral` |
| NVIDIA | `nvidia` |
| OpenRouter | `openrouter` |
| OpenAI-kompatible APIs | `openai-compatible` |

Beispiel:

```ini
PROVIDER=openrouter
```

Wähle **einen** Wert und lasse nur eine `PROVIDER=`-Zeile in der Datei stehen. `openai-compatible` ist für einen OpenAI-kompatiblen API-Endpunkt gedacht; dafür trägst du zusätzlich dessen `BASE_URL=` ein.

Der **API-Key gehört ausschließlich auf den Gateway, niemals in `AI4DOS.CFG`**. In nativen Paketen trägst du ihn bei `API_KEY=` in `server/provider.local.cfg` ein. Bei Docker / Portainer trägst du ihn bei `API_KEY=` in `config.local/provider.cfg` ein.

## 3. Modell auswählen

AI4DOS pflegt keine feste Modellliste. Trage bei `MODEL=` die Modell-ID exakt so ein, wie sie der jeweilige API-Anbieter bezeichnet. Den genauen Modellnamen bitte aus der API-/Developer-Dokumentation des jeweiligen Anbieters entnehmen.

Der Anbieter entscheidet, ob die Modell-ID verfügbar und für deinen API-Zugang freigegeben ist.

Für den einfachen kostenlosen Einstieg mit OpenRouter kannst du den vorbereiteten Standardwert `MODEL=openrouter/free` zunächst unverändert lassen. OpenRouter kann dann ein aktuell verfügbares kostenloses Modell auswählen. Wenn du später ein bestimmtes Modell nutzen möchtest, trägst du dessen Modell-ID bei `MODEL=` ein.

Das ist keine Zusage, dass jedes Modell oder jede Sonderoption funktioniert. Diese Seite ist kein Live-Modellkatalog und bestätigt keine Live-Validierung einzelner Modelle.

## 4. Reasoning / Thinking

Der globale Default ist:

```ini
REASONING=none
```

Damit fordert AI4DOS keine zusätzliche optionale Reasoning-Funktion an. Das schützt vor ungefragt aktivierten Betriebsarten, die mehr Tokens und zusätzliche Kosten verursachen können. Es bedeutet nicht, dass sich internes Denken bei jedem Modell vollständig abschalten lässt.

Lasse den Default für den Einstieg stehen. Provider- und modellspezifische Thinking-Optionen können abweichen; aktiviere sie nur bewusst und nach Prüfung der jeweiligen API- und Kostenangaben.

Diese Werte akzeptiert die AI4DOS-Konfiguration; welche davon ein Modell unterstützt, hängt von dessen API ab:

| Eintrag | Werte | Geltung |
| --- | --- | --- |
| `REASONING` | `none` (Default), `minimal`, `low`, `medium`, `high`, `xhigh`, `max` | Allgemeine Vorgabe; der jeweilige Adapter ordnet sie der API zu. |
| `REASONING_EFFORT` | `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max` | OpenAI Responses, Anthropic, Mistral, NVIDIA, OpenRouter und OpenAI-kompatible APIs; überschreibt `REASONING`. |
| `THINKING_LEVEL` | `minimal`, `low`, `medium`, `high` | Nur Gemini; überschreibt dort `REASONING`. |
| `THINKING_BUDGET` | Gemini: ganze Zahl ab `-1`; Claude: `1024` bis kleiner als `MAX_OUTPUT_TOKENS` | Explizites Thinking-Budget; kann auch bei `REASONING=none` Thinking aktivieren. |

Bei Gemini darfst du nur **einen** der Einträge `THINKING_LEVEL` und `THINKING_BUDGET` setzen. AI4DOS reicht das Budget unverändert an die API weiter; die Bedeutung und unterstützte Spanne bestimmt das Modell. Gemini 2.5 benötigt zum bewussten Aktivieren ein explizites Budget; ohne Override akzeptiert Gemini nur `minimal`, `low`, `medium`, `high` als aktive Reasoning-Stufen. Bei `REASONING=none` setzt AI4DOS für die bekannten Gemini-2.5-Flash/Flash-Lite-IDs ein Budget von `0`; bei anderen IDs bleibt die API-Vorgabe bestehen.

Claude akzeptiert kein `minimal`. Modelle mit manuellem Thinking benötigen `THINKING_BUDGET`; dafür muss `MAX_OUTPUT_TOKENS` größer als das Budget sein. Adaptive Modelle verwenden eine Effort-Stufe ohne manuelles Budget; `xhigh` ist auf bestimmte adaptive Modelle begrenzt. Bei manuellem Budget unterstützen Haiku/Sonnet 4.5 keine zusätzliche Effort-Stufe, Opus 4.5 nur `low`, `medium`, `high`. Bei `mistral-small-latest` und `mistral-medium-3-5` akzeptiert AI4DOS nur `none` oder `high`.

OpenRouter übersetzt `none` in `reasoning.enabled=false`. OpenAI sendet den automatischen Wert `none` nur für die im Adapter hinterlegten IDs `gpt-6-luna`, `gpt-6-sol` und `gpt-5.1`; sonst wird ohne Override kein Effort-Wert gesendet. Bei NVIDIA gelten zusätzlich die im Adapter hinterlegten Modellvorgaben. Die vollständige technische Zuordnung einschließlich der Claude- und NVIDIA-Ausnahmen steht in der [DEV-Dokumentation](../dev/providers.md#reasoning-and-thinking). Ungültige Kombinationen können den Gateway-Start verhindern oder vom Provider abgelehnt werden.

Explizite Overrides können unabhängig von `REASONING=none` wirksam sein. Entferne sie, wenn du zu den Standardwerten zurückkehren möchtest.

Speichere Änderungen und starte den Gateway wie in deiner Installationsanleitung neu: [Windows](install-windows.md#später-ändern), [macOS](install-macos.md#später-ändern), [Linux](install-linux.md#später-ändern) oder [Docker / Portainer](install-docker.md#9-später-ändern). Bei Fehlern hilft die [Fehlerbehebung](troubleshooting.md).

## Antwortlänge und Transport

Für den Einstieg sind die Standardlimits sinnvoll. Wenn du bewusst kürzere oder längere Antworten möchtest, kannst du `MAX_OUTPUT_TOKENS=` in der aktiven Providerdatei ergänzen (Default `1024`). Das zusätzliche Gateway-Limit `max_reply_bytes` steht in der Gateway-JSON (Default `65536` UTF-8-Bytes). Speichere Änderungen und starte den Gateway neu. Diese Limits sind vom DOS-Speicher und dem [Scrollback/Transcript](dos-setup.md#dos-client-bedienen) unabhängig. Größere Antworten werden in mehreren kleinen Datenblöcken übertragen, nicht als ein riesiger Netzwerkblock.

`MAX_OUTPUT_TOKENS` muss eine positive ganze Zahl sein; AI4DOS setzt dafür keine feste Obergrenze, der Provider jedoch schon. Tokens sind keine feste Zahl von Zeichen oder Bytes. Wenn das Modell wegen des Tokenlimits unvollständig endet, behandeln die Adapter dies als `UPSTREAM`-Fehler statt als vollständige Antwort.

Überschreitet eine Antwort `max_reply_bytes`, bricht der Gateway mit `UPSTREAM` (`response generation failed`) ab. Im normalen DOS-Ausgabemodus wird die Antwort erst nach vollständigem Empfang gerendert und übertragen; dann kommt bei diesem Fehler kein Antworttext an. Im UTF-8-Ausgabemodus können bereits übertragene Teile sichtbar bleiben. Eine abgebrochene Antwort und die zugehörige neue Nutzernachricht werden nicht in den Gateway-Modellkontext aufgenommen.

Der DOS-Transcript hat insgesamt **61.440 Bytes (60 KiB)** Platz, einschließlich Labels, Zeilenumbrüchen und interner Datensatzverwaltung. Ab **51.200 Bytes (50 KiB)** erscheint „Chatverlauf fast voll“. Reicht der Restplatz nicht, erscheint „Chatverlauf voll“: Der Client zeigt und speichert nur den noch passenden Antwortteil und blockiert weitere Nachrichten. Speichere mit F5 und beginne mit F2 einen neuen Chat. Wie viel von der nächsten Antwort hineinpasst, hängt vom bereits belegten Speicher ab. Ein größeres Gateway-Limit vergrößert diesen Speicher nicht; eine im Gateway vollständig abgeschlossene Antwort kann trotz lokal gekürzter Anzeige vollständig im Modellkontext stehen.

Die offiziellen Provider werden per HTTPS angesprochen. Ein bewusst konfigurierter `openai-compatible`-Endpunkt kann auch HTTP verwenden. Das ändert nichts am unverschlüsselten DOS↔Gateway-Verkehr.

## Offline-Funktionstest ohne API-Zugang

Mit dem integrierten Mock-Provider kannst du AI4DOS testen, ohne einen API-Zugang oder API-Key zu benötigen.

Öffne die Provider-Konfigurationsdatei (`server/provider.local.cfg`, bei Docker `config.local/provider.cfg`) und verwende folgende Einstellungen:

```ini
PROVIDER=mock
MODEL=mock
API_KEY=
REASONING=none
```

**Wichtig:** Falls du zuvor einen anderen Provider verwendet hast, entferne dessen zusätzliche Einstellungen aus der Datei oder kommentiere sie mit `#` oder `;` aus. Am einfachsten verwendest du für den Test eine frische Kopie der mitgelieferten Provider-Konfiguration.

Starte anschließend den Gateway neu und sende eine Nachricht über AI4DOS. Du erhältst eine Antwort, die mit `Test reply:` beginnt und deine Nachricht wiederholt.

Der normale Device-Key und eine funktionierende Netzwerkverbindung zwischen DOS-PC und Gateway bleiben erforderlich.
