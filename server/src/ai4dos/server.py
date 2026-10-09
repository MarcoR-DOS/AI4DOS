import argparse
import asyncio
import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass
from collections import defaultdict
from . import __version__
from .config import ConfigurationError, Settings, build_provider
from .protocol import GREETING, MAX_LINE, ProtocolError, parse_command, data_frames, error_frame
from .output import render_dos
from .session import Session
from .provider import ProviderError

LOG = logging.getLogger("ai4dos")


@dataclass
class StoredSession:
    device: str
    session: Session
    touched: float
    owner: object = None


class Gateway:
    def __init__(self, settings, provider):
        self.settings, self.provider = settings, provider
        self.active = defaultdict(int)
        self.tasks = set()
        self.sessions = {}
        self.preauth_connections = 0

    def expire_sessions(self):
        now = time.monotonic()
        for sid, stored in list(self.sessions.items()):
            if stored.owner is None and now - stored.touched >= self.settings.session_ttl:
                del self.sessions[sid]

    def release_session(self, stored, writer):
        if stored is not None and stored.owner is writer:
            stored.owner = None
            stored.touched = time.monotonic()

    async def start(self):
        return await asyncio.start_server(self.handle, self.settings.host, self.settings.port, limit=MAX_LINE + 2)

    async def write(self, writer, line):
        writer.write((line + "\r\n").encode("utf-8"))
        await asyncio.wait_for(writer.drain(), self.settings.idle_timeout)

    async def respond(self, writer, session, message):
        # Only fixed product labels cross the wire; no model/config text.
        label = getattr(self.provider, "label", "AI")
        if label not in {"ChatGPT", "Claude", "Gemini", "Mistral", "NVIDIA", "OpenRouter"}:
            label = ""
        await self.write(writer, "BEGIN" + (" " + label if label else ""))
        parts, total = [], 0
        stream = self.provider.stream(session.request(message))
        try:
            async for delta in stream:
                total += len(delta.encode("utf-8"))
                if total > self.settings.max_reply_bytes:
                    raise ValueError("reply limit")
                parts.append(delta)
                if self.settings.output_mode == "utf8":
                    for frame in data_frames(delta):
                        await self.write(writer, frame)
            reply = "".join(parts)
            if not reply:
                raise ValueError("empty reply")
            if self.settings.output_mode == "dos":
                for frame in data_frames(render_dos(reply)):
                    await self.write(writer, frame)
            await self.write(writer, "END")
            session.record(message, reply)
        finally:
            await stream.aclose()

    async def handle(self, reader, writer):
        loop = asyncio.get_running_loop()
        auth_deadline = loop.time() + self.settings.auth_timeout
        task = asyncio.current_task()
        self.tasks.add(task)
        authenticated = None
        hello = None
        challenge = None
        session = None
        stored = None
        preauth_slot = False
        auth_timer = None
        auth_expired = False

        def expire_auth():
            nonlocal auth_expired
            auth_expired = True
            task.cancel()

        try:
            if self.preauth_connections >= self.settings.max_unauthenticated_connections:
                await asyncio.wait_for(self.write(writer, error_frame("LIMIT", "connection limit")), 1.0)
                return
            self.preauth_connections += 1
            preauth_slot = True
            # One absolute deadline covers greeting, reads and writes; commands cannot reset it.
            auth_timer = loop.call_at(auth_deadline, expire_auth)
            await self.write(writer, GREETING)
            while True:
                try:
                    raw = await asyncio.wait_for(reader.readline(), self.settings.idle_timeout)
                    if not raw:
                        break
                    if not raw.endswith(b"\n") or len(raw.rstrip(b"\r\n")) > MAX_LINE:
                        raise ProtocolError("LINE_TOO_LONG", "command exceeds limit")
                    line = raw[:-1].removesuffix(b"\r").decode("utf-8")
                    verb, argument = parse_command(line)
                except (UnicodeDecodeError, ProtocolError) as exc:
                    if isinstance(exc, ProtocolError):
                        await self.write(writer, error_frame(exc.code, exc.message))
                    else:
                        await self.write(writer, error_frame("BAD_ENCODING", "expected UTF-8"))
                    continue
                except (ValueError, asyncio.LimitOverrunError):
                    await self.write(writer, error_frame("LINE_TOO_LONG", "command exceeds limit"))
                    break
                if authenticated is None and loop.time() >= auth_deadline:
                    auth_timer.cancel()
                    auth_expired = True
                    raise asyncio.CancelledError
                if verb == "QUIT":
                    await self.write(writer, "OK BYE")
                    break
                if verb == "HELLO":
                    if hello is not None or authenticated is not None:
                        await self.write(writer, error_frame("BAD_STATE", "HELLO already received"))
                    else:
                        hello = argument
                        challenge = secrets.token_hex(32)
                        await self.write(writer, "CHALLENGE " + challenge)
                    continue
                if verb == "AUTH":
                    if not challenge or authenticated is not None:
                        await self.write(writer, error_frame("BAD_STATE", "no active challenge"))
                        continue
                    secret = self.settings.devices.get(hello)
                    expected = hmac.new((secret or secrets.token_hex(32)).encode("ascii"), challenge.encode("ascii"), hashlib.sha256).hexdigest()
                    challenge = None  # Single use, also after a failed attempt.
                    if not hmac.compare_digest(expected, argument) or secret is None:
                        peer = writer.get_extra_info("peername")
                        peer_ip = peer[0] if peer else "unknown"
                        LOG.warning("AUTH_FAILED peer=%s device=%s", peer_ip, hello)
                        await self.write(writer, error_frame("AUTH_FAILED", "device authentication failed"))
                        break
                    if self.active[hello] >= self.settings.max_connections_per_device:
                        await self.write(writer, error_frame("LIMIT", "device connection limit"))
                        break
                    authenticated = hello
                    self.active[hello] += 1
                    auth_timer.cancel()
                    self.preauth_connections -= 1
                    preauth_slot = False
                    await self.write(writer, "OK AUTH")
                    continue
                if authenticated is None:
                    await self.write(writer, error_frame("AUTH_REQUIRED", "authenticate device first"))
                    continue
                if verb in {"NEW", "RESUME"}:
                    self.expire_sessions()
                    if verb == "RESUME":
                        candidate = self.sessions.get(argument)
                        # Same failure for missing, expired and foreign IDs.
                        if candidate is None or candidate.device != authenticated:
                            await self.write(writer, error_frame("SESSION", "session unavailable"))
                            continue
                        if candidate.owner is not None and candidate.owner is not writer:
                            await self.write(writer, error_frame("SESSION_BUSY", "session already connected"))
                            continue
                    else:
                        own = [x for x in self.sessions.values() if x.device == authenticated]
                        if len(own) >= self.settings.max_sessions_per_device:
                            unused = [x for x in own if x.owner is None or x.owner is writer]
                            if not unused:
                                await self.write(writer, error_frame("LIMIT", "session limit"))
                                continue
                            oldest = min(unused, key=lambda x: x.touched)
                            del self.sessions[oldest.session.session_id]
                        fresh = Session()
                        while fresh.session_id in self.sessions:
                            fresh = Session()
                        candidate = StoredSession(authenticated, fresh, time.monotonic())
                        self.sessions[fresh.session_id] = candidate
                    self.release_session(stored, writer)
                    stored = candidate
                    stored.owner = writer
                    stored.touched = time.monotonic()
                    session = stored.session
                    await self.write(writer, "SESSION " + session.session_id if verb == "NEW" else "OK RESUME")
                elif session is None:
                    await self.write(writer, error_frame("BAD_STATE", "send NEW first"))
                else:
                    try:
                        await asyncio.wait_for(self.respond(writer, session, argument), self.settings.request_timeout)
                    except (ConnectionError, asyncio.CancelledError):
                        raise
                    except ProviderError as exc:
                        LOG.warning("provider request failed: %s", exc.code)
                        await self.write(writer, error_frame(exc.code, exc.message))
                    except Exception as exc:
                        LOG.warning("provider request failed: %s", type(exc).__name__)
                        await self.write(writer, error_frame("UPSTREAM", "response generation failed"))
        except asyncio.CancelledError:
            if not auth_expired:
                raise
            # Best effort only: a peer that does not read must not hold the slot indefinitely.
            try:
                await asyncio.wait_for(self.write(writer, error_frame("AUTH_REQUIRED", "authentication timeout")), 1.0)
            except (ConnectionError, asyncio.TimeoutError):
                pass
        except (ConnectionError, asyncio.TimeoutError):
            pass
        finally:
            if auth_timer is not None:
                auth_timer.cancel()
            if preauth_slot:
                self.preauth_connections -= 1
            self.release_session(stored, writer)
            if authenticated is not None:
                self.active[authenticated] -= 1
                if not self.active[authenticated]:
                    del self.active[authenticated]
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass
            self.tasks.discard(task)

    async def close(self):
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.sessions.clear()
        await self.provider.close()


async def run(path, host=None, port=None):
    from pathlib import Path
    if not Path(path).is_file():
        raise ConfigurationError("Gateway config is missing. Check the file selected with --config; Docker mounts it at /config/gateway.json.")
    settings = Settings.load(path)
    if host is not None:
        settings.host = host
    if port is not None:
        settings.port = port
    gateway = Gateway(settings, build_provider(settings))
    try:
        try:
            server = await gateway.start()
        except OSError:
            raise ConfigurationError("Cannot listen on port %s. Check the host address, port and another running gateway." % settings.port) from None
        print("AI4DOS gateway ready on port %s. Version %s. Stop with Ctrl+C." % (server.sockets[0].getsockname()[1], __version__), flush=True)
        async with server:
            await server.serve_forever()
    finally:
        await gateway.close()


def main():
    parser = argparse.ArgumentParser(description="AI4DOS self-hosted gateway")
    parser.add_argument("--config", default="server/gateway.local.json", help="local JSON configuration")
    parser.add_argument("--host", help="listener address override (container runtime)")
    parser.add_argument("--port", type=int, metavar="PORT", help="listener port override (container runtime)")
    parser.add_argument("--version", action="version", version="AI4DOS " + __version__)
    args = parser.parse_args()
    if args.port is not None and not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(run(args.config, args.host, args.port))
    except KeyboardInterrupt:
        pass
    except ConfigurationError as exc:
        raise SystemExit(str(exc)) from None
    except FileNotFoundError:
        raise SystemExit("Configuration file is missing. Check provider_config and API_KEY_FILE.") from None
    except ImportError:
        raise SystemExit("Gateway dependencies are missing. Run the dependency setup commands from the AI4DOS installation guide.") from None
    except Exception:
        # Arbitrary JSON, SDK and OS exception strings may contain secrets.
        raise SystemExit("Provider configuration invalid or gateway startup failed. Check the AI4DOS installation guide and your local configuration.") from None


if __name__ == "__main__":
    main()
