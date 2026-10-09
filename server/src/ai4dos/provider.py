from typing import Protocol, AsyncIterator
import asyncio
import json
from .session import Message, Role
import logging
import httpx


ERROR_MESSAGES = {
    "UPSTREAM_AUTH": "provider authentication failed",
    "UPSTREAM_MODEL": "provider model unavailable",
    "UPSTREAM_RATE_LIMIT": "provider rate limit reached",
    "UPSTREAM_UNAVAILABLE": "provider unavailable",
    "UPSTREAM": "response generation failed",
}


class ProviderError(RuntimeError):
    """Only fixed, public-safe codes/messages cross the adapter boundary."""
    def __init__(self, code="UPSTREAM"):
        self.code = code if code in ERROR_MESSAGES else "UPSTREAM"
        self.message = ERROR_MESSAGES[self.code]
        super().__init__(self.message)


def classify_error(exc):
    if isinstance(exc, ProviderError):
        return exc
    from openai import APIConnectionError, APITimeoutError
    if isinstance(exc, (APIConnectionError, APITimeoutError, TimeoutError, httpx.TransportError)):
        return ProviderError("UPSTREAM_UNAVAILABLE")
    status = getattr(exc, "status_code", None)
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        body = body.get("error", body)
    code = body.get("code") if isinstance(body, dict) else None
    if isinstance(code, int) and status is None:
        status = code
    if status == 400 and isinstance(body, dict) and body.get("param") == "model":
        code = "invalid_model"
    return provider_error(status, code)


def provider_error(status=None, code=None):
    # Deliberately never copy the upstream message, URL, request or response body.
    if status in (401, 403) or code in ("invalid_api_key", "authentication_error"):
        return ProviderError("UPSTREAM_AUTH")
    if code in ("model_not_found", "invalid_model", "unknown_model") or status == 404:
        return ProviderError("UPSTREAM_MODEL")
    if status == 429 or code in ("rate_limit_exceeded", "rate_limit_error"):
        return ProviderError("UPSTREAM_RATE_LIMIT")
    if status in (408, 502, 503, 504) or code in ("service_unavailable", "connection_error"):
        return ProviderError("UPSTREAM_UNAVAILABLE")
    return ProviderError()


def wire_messages(messages):
    roles = {Role.ROLE_USER: "user", Role.ROLE_AI: "assistant", Role.ROLE_SYSTEM: "system"}
    return [{"role": roles[m.role], "content": m.text} for m in messages]


DOS_CAPABILITIES = (
    "The client is a text-based DOS client. It cannot open URLs or display images or files. "
    "The user cannot upload or provide files, images, or other content through this client; "
    "only typed chat text is supported. Do not ask the user to upload or provide such content "
    "or perform other actions unsupported by the client. Ask for a typed description when needed. "
    "Respond in the language used by the user unless the user asks for another language."
)


def provider_instructions(instructions):
    """Technical baseline for every provider, independent of device identity."""
    return DOS_CAPABILITIES + ("\n\n" + instructions if instructions else "")


def make_http_client():
    for logger in ("openai", "httpx", "httpcore"):
        logging.getLogger(logger).setLevel(logging.WARNING)
    return httpx.AsyncClient(trust_env=False, timeout=120)


def make_client(api_key, base_url):
    from openai import AsyncOpenAI
    # Runtime keys only; no automatic retries/proxies or SDK debug request logs.
    return AsyncOpenAI(api_key=api_key, base_url=base_url, max_retries=0,
                      http_client=make_http_client())


async def sse_events(response):
    """Native SSE records, including multiline data and a final record at EOF."""
    data = []
    async for line in response.aiter_lines():
        if not line:
            if data:
                yield json.loads("\n".join(data))
                data = []
        elif line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
    if data:
        yield json.loads("\n".join(data))


class Provider(Protocol):
    model: str
    label: str
    def stream(self, messages: list[Message]) -> AsyncIterator[str]: ...
    async def close(self): ...


class MockProvider:
    """Deterministic neutral test provider; not an AI service."""
    model = "mock"
    label = "AI"

    async def stream(self, messages):
        for part in ["Test reply: ", messages[-1].text, "\n"]:
            await asyncio.sleep(0.01)
            yield part

    async def close(self):
        pass
