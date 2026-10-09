# AI4DOS Wire Protocol 0.3

TCP, UTF-8, lines terminated by CRLF (the gateway also accepts LF). Version 0.3 adds an optional visible provider label to the BEGIN frame.
The new client also accepts the 0.2 banner and BEGIN without a label. Older
0.2 clients require a client update to use a 0.3 gateway.

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

HMAC-SHA256 uses the local Device-Secret as the key and the 64
ASCII characters of the challenge as the message (no hex decoding). The challenge
and authentication are bound to the connection; a challenge can only be used once.
Errors: `ERROR <code> <message>`. Authentication errors and the connection limit close the
connection; response errors do not produce END. QUIT is also allowed without a session.

Device-ID: 1–64 characters consisting of ASCII letters, digits, period, hyphen, and underscore.
Secret: 8–128 printable ASCII characters without spaces. A maximum of 1024 bytes
per command line excluding CRLF; MSG text is limited to 1000 UTF-8 bytes.
The DATA payload is limited to 512 bytes after escaping; UTF-8 characters and escape sequences
are not split. Escapes: `\\`, `\r`, `\n`, `\t`.

NEW replaces the session of this connection. RESUME <session-id> reconnects an
existing session belonging to the same authenticated device; success: OK RESUME.
A session connected elsewhere yields SESSION_BUSY; a missing session yields SESSION.
Sessions remain local to the process and do not survive a gateway restart. No output mode command. Device-ID only affects authentication and limits.
Internal roles: ROLE_USER, ROLE_AI, ROLE_SYSTEM. Visible labels are separate.

In DOS mode, the gateway first consumes the entire provider stream,
then formats the response and sends DATA/END. BEGIN is sent beforehand. The
client outputs each DATA immediately. The optional gateway mode utf8 sends
provider deltas directly; the client converts UTF-8 to the selected DOS code page.

Provider labels are ChatGPT, Claude, Gemini, Mistral, NVIDIA, and OpenRouter.
Mock, openai-compatible, and unknown providers send BEGIN without a label; the
client then displays AI or KI depending on the language. Unknown printable labels
are also displayed using the fallback. Each response supplies its label anew,
including after RESUME/reconnect. The label affects neither roles nor sessions.
Transcript/Save retain the label visible at the start of the message.
