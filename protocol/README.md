# AI4DOS Wire Protocol 0.3

TCP, UTF-8, Zeilen mit CRLF (Gateway akzeptiert auch LF). Version 0.3 ergänzt ein optionales sichtbares Providerlabel im BEGIN-Frame.
Der neue Client akzeptiert auch das 0.2-Banner und BEGIN ohne Label. Alte
0.2-Clients benötigen für einen 0.3-Gateway ein Clientupdate.

```text
S: OK AI4DOS/0.3 UTF-8
C: HELLO <device-id>
S: CHALLENGE <64 lowercase hex characters>
C: AUTH <HMAC-SHA256 hex>
S: OK AUTH
C: NEW
S: SESSION <12 lowercase hex characters>
C: MSG <text>
S: BEGIN [<provider-label>]
S: DATA <escaped text>
S: END
C: QUIT
S: OK BYE
```

HMAC-SHA256 verwendet das lokale Device-Secret als Schlüssel und die 64
ASCII-Zeichen der Challenge als Nachricht (keine Hex-Dekodierung). Challenge
und Authentifizierung sind verbindungsgebunden; eine Challenge ist einmalig.
Fehler: `ERROR <code> <message>`. Auth-Fehler und Verbindungslimit schließen die
Verbindung; Antwortfehler liefern kein END. QUIT ist auch ohne Session zulässig.

Device-ID: 1–64 Zeichen aus ASCII-Buchstaben, Ziffern, Punkt, Minus, Unterstrich.
Secret: 8–128 druckbare ASCII-Zeichen ohne Leerzeichen. Maximal 1024 Bytes
pro Befehlszeile ohne CRLF, MSG-Nutztext maximal 1000 UTF-8-Bytes.
DATA-Nutzlast maximal 512 Bytes nach Escaping; UTF-8-Zeichen und Escape-Sequenzen
werden nicht geteilt. Escapes: `\\`, `\r`, `\n`, `\t`.

NEW ersetzt die Session dieser Verbindung. RESUME <session-id> verbindet eine
noch vorhandene Session desselben authentifizierten Geräts erneut; Erfolg: OK RESUME.
Eine anderweitig verbundene Session ergibt SESSION_BUSY, eine fehlende SESSION.
Sessions bleiben prozesslokal und überleben keinen Gatewayrestart. Kein Output-Modus-Befehl. Device-ID beeinflusst nur Auth und Limits.
Interne Rollen: ROLE_USER, ROLE_AI, ROLE_SYSTEM. Sichtbare Labels sind separat.

Im DOS-Modus konsumiert das Gateway zunächst den kompletten Providerstream,
formatiert dann die Antwort und sendet DATA/END. BEGIN erscheint davor. Der
Client gibt jedes DATA sofort aus. Der optionale Gateway-Modus utf8 sendet
Provider-Deltas direkt; der Client konvertiert UTF-8 für die gewählte DOS-Codepage.

Providerlabels sind ChatGPT, Claude, Gemini, Mistral, NVIDIA und OpenRouter.
Mock, openai-compatible und unbekannte Provider senden BEGIN ohne Label; der
Client zeigt dann sprachabhängig AI oder KI. Unbekannte druckbare Labels
werden ebenfalls als Fallback dargestellt. Jede Antwort liefert ihr Label neu,
auch nach RESUME/Reconnect. Das Label beeinflusst weder Rollen noch Sessions.
Transcript/Save behalten das beim Nachrichtenbeginn sichtbare Label.
