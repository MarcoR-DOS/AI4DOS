# Architecture

[Developer index](README.md) · [DOS client](dos-client.md) · [Gateway](gateway.md)

```text
DOS keyboard / 80x25 UI / local transcript
                |
       16-bit C/C++ client
       Packet Driver + linked mTCP
                |
       plain TCP, UTF-8 line frames
                |
       asyncio Python gateway
       auth -> device-bound session -> provider adapter
                |
       HTTPS / TLS to configured provider API
```

## Component boundaries

The client is a DOS-MZ executable targeting 8086/8088 real mode, with no DOS
extender. Open Watcom's compiler programs may themselves use an extender; that
is distinct from the application they produce. The client handles keyboard input,
text video, DOS encoding, authentication, protocol parsing, scrollback and saving.
It statically links selected mTCP modules through
[mtcpadpt.cpp](../../client/src/mtcpadpt.cpp). A working Packet Driver and mTCP
network configuration are external runtime prerequisites.

The modern gateway owns TLS, HTTP clients, provider credentials and API-specific
payloads. All presets use HTTPS upstream; `openai-compatible` also accepts a
configured HTTP API root. The provider API key never belongs on the DOS side.
The device secret is a separate credential shared by client and gateway.

DOS-to-gateway TCP is unencrypted. HMAC authenticates the device using a fresh
challenge; it does not encrypt chat messages or authenticate each later frame.
Deployment network controls must account for this boundary; the code does not
implement TLS on the DOS link.

## Message and output flow

[main.c](../../client/src/main.c) converts typed DOS text to UTF-8 and sends a
message through the [client parser](../../client/src/protocol.c).
[Gateway.respond](../../server/src/ai4dos/server.py) constructs the request from
session history plus the new user message and sends `BEGIN` before reading the
provider stream. Labels are presentation metadata, independent of internal roles.

With the default `output_mode=dos`, the gateway consumes the complete provider
stream, enforces the reply-byte limit, then applies
[render_dos](../../server/src/ai4dos/output.py) and sends text frames followed by
`END`. The client displays each received `DATA` immediately. This is not
provider-token streaming to the DOS screen. In `output_mode=utf8`, provider text
deltas go directly to the wire, while the gateway still accumulates the reply for
history. Both paths require successful completion and a nonempty reply.

Formatting is presentation only: session history records the unformatted provider
reply, after successful `END` delivery. The DOS transcript stores the displayed
DOS text and labels instead. These are different histories with different limits.
Local `ROLE_SYSTEM` connection notices stay visible and saveable on the client;
they never enter a provider request. Gateway capability instructions are a
separate server-side system prompt.

## Three kinds of state

| State | Owner | Lifetime |
| --- | --- | --- |
| Screen scrollback and save transcript | DOS process | Cleared on successful new chat; lost on process exit unless saved |
| Authenticated connection and challenge | TCP handler | Bound to one connection; new connection requires new authentication |
| Conversation session and model history | Gateway process | Can outlive a disconnected socket; expires/evicts in memory; lost on gateway restart |

Reconnect establishes a new socket and performs fresh HMAC authentication.
Resume then reattaches the retained session ID for the same device. It does not
replay missing output or resume an interrupted provider stream. F2/new chat
selects a fresh conversation and clears the local chat after success. The gateway
may retain the previous detached conversation until expiry or eviction.

The precise frames, limits and compatibility behavior remain in the separate
[Wire Protocol](../../protocol/README.md), with implementations in
[server protocol.py](../../server/src/ai4dos/protocol.py) and the client parser.
Do not copy the full protocol or tie its version to ordinary documentation changes.
