# Gateway implementation

[Developer index](README.md) · [Architecture](architecture.md) · [Providers](providers.md)

## Runtime and configuration boundaries

[server.py](../../server/src/ai4dos/server.py) provides an asyncio TCP listener and
one handler task per connection. A gateway instance owns one configured provider,
active-device counters, pre-auth slots and an in-memory session registry. There is
no per-device provider routing or durable session database.

[Settings](../../server/src/ai4dos/config.py) loads gateway JSON. Listener, device
keys, output mode, instructions and lifecycle limits belong to that configuration.
`provider_config` selects a KEY=VALUE file relative to the gateway JSON directory.
Its provider identity/model/key/API/reasoning fields replace their JSON counterparts;
optional generation fields absent from that file may still inherit JSON values.
`API_KEY_FILE` is relative to the provider file (or JSON if no provider file).
Unknown/duplicate provider fields and unsupported combinations fail startup.

The factory selects one preset or mock. Key resolution is explicit key file,
otherwise inline `API_KEY`, provider-specific environment variable, then generic
`API_KEY`. These are gateway credentials, never device secrets. The client only
has gateway address/port, device identity, shared device secret and UI options.
See the platform setup guides for [Windows](../en/install-windows.md),
[macOS](../en/install-macos.md), [Linux](../en/install-linux.md) and
[Docker / Portainer](../en/install-docker.md) for gateway field entry, the
[DOS client configuration](../en/dos-setup.md#c-configure-the-dos-client-ai4doscfg)
for client fields, and [provider options](providers.md) for adapter-specific interpretation.

## Authentication and connection limits

A new connection consumes a pre-auth slot before greeting. Default
`max_unauthenticated_connections` is **16**; excess sockets get a best-effort
`LIMIT` response and close. An absolute **30-second** `auth_timeout` covers greeting,
reads and writes through authentication. Commands cannot refresh the deadline.
Expiry cancels the handler, attempts a bounded error write and frees the slot.
These settings must be finite/positive, with an integer connection cap.

HELLO creates `secrets.token_hex(32)`: 64 lowercase hexadecimal ASCII characters.
HMAC-SHA256 uses the device secret as key and those ASCII characters as message,
not hex-decoded bytes. The gateway uses `hmac.compare_digest`; a challenge is
connection-bound and consumed even on failure. Unknown devices receive the same
public auth failure. Only authenticated devices may create/resume a session or
trigger a provider request. Successful auth transfers the connection from the
pre-auth pool to the per-device count, default **2** connections. This is bounded
admission and timeout handling, not a general distributed rate limiter.

## Session binding and lifetime

A stored session contains device ID, history, last-touch time and an owner writer.
IDs are 12 lowercase hex characters from `token_hex(6)`. `RESUME` requires the same
authenticated device and an unowned session (or the current writer); a different
owner produces `SESSION_BUSY`. Missing, expired and foreign IDs share the public
`SESSION` failure. Disconnect releases ownership and starts the detached TTL.

Default `session_ttl` is **3600 seconds**, `max_sessions_per_device` **32**.
Expiry is lazy, when NEW/RESUME triggers registry cleanup, and only affects detached
sessions. At the cap, NEW evicts the oldest eligible detached/current-owned entry;
it cannot evict a session owned by another connection. NEW releases the previous
binding, which can remain as a detached registry entry. All state disappears at
gateway restart or shutdown.

[Session](../../server/src/ai4dos/session.py) retains the last **10 successful
exchanges** (20 user/assistant messages). `request()` adds the current user message
without committing it yet. Only a complete, nonempty answer followed by successful
END delivery is recorded. A failed/interrupted request is not a resumable stream.

## Provider instructions and output limits

Every real adapter applies [provider_instructions()](../../server/src/ai4dos/provider.py):
DOS supports typed text only, cannot open URLs/display images/files or upload
content, and should be offered typed alternatives. Replies should follow the
user's language unless another language is requested. The configurable
`instructions` are appended to this technical baseline; device IDs carry no persona
or capabilities. Mock is deterministic and does not consult an external model.

Default limits are 65,536 UTF-8 reply bytes, 120 seconds per provider response and
300 seconds idle/read/write timeout. Overflow, empty output and unclassified
response failures become safe generic `UPSTREAM` errors. Typed `ProviderError`
categories survive to the wire. Errors do not synthesize `END` or record history.
In utf8 mode, text already sent before an error cannot be recalled. In dos mode,
formatting/output waits for complete upstream success; see [architecture](architecture.md).

## Logging and containers

Provider boundaries emit only fixed public error categories/messages. Gateway
warnings use error codes or exception type names, not raw API bodies/config values.
AUTH_FAILED logging includes peer IP and validated device ID, not secret/HMAC/
challenge. API keys are excluded from Settings repr. Shared HTTP clients disable
inherited proxies (`trust_env=False`), use a 120-second HTTP timeout and quiet
OpenAI/httpx/httpcore loggers. SDK adapters disable automatic retries. Do not enable
raw request/debug logging with private credentials; fixed messages and pattern
scans do not guarantee arbitrary custom logging is safe.

[Dockerfile](../../Dockerfile) overrides the listener to **0.0.0.0:1983 inside the
container**, regardless of the native template's 127.0.0.1 default.
[Compose](../../docker-compose.yml) and [Portainer](../../portainer-stack.yml) publish
`${AI4DOS_BIND_ADDRESS:-0.0.0.0}:${AI4DOS_PORT:-1983}:1983`. Changing the published
host port does not change the internal port. EXPOSE alone does not publish a port.
The config files mount read-only at `/config/gateway.json` and `/config/provider.cfg`;
root is read-only, capabilities are dropped and no-new-privileges is enabled.
Portainer requires an already local `ai4dos-gateway:beta` image and explicit absolute
host config paths; its web editor does not import a local `.env`. Native starters
use the JSON listener unless command-line `--host`/`--port` overrides are provided.
