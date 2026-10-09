"""Native Claude Messages API; shared text, limits, errors and HTTP lifecycle."""
from .provider import (ProviderError, classify_error, make_http_client,
                       provider_error, provider_instructions, wire_messages, sse_events)
from .textfilter import ExactTokenFilter


# Reviewed against Anthropic's thinking/effort table, 2026-10-06.
MANUAL = {"claude-haiku-4-5", "claude-haiku-4-5-20251001",
          "claude-sonnet-4-5", "claude-sonnet-4-5-20250929",
          "claude-opus-4-5", "claude-opus-4-5-20251101",
          "claude-opus-4-6", "claude-sonnet-4-6"}
ADAPTIVE = {"claude-opus-4-6", "claude-sonnet-4-6", "claude-opus-4-7",
            "claude-opus-4-8", "claude-opus-5", "claude-sonnet-5",
            "claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5",
            "claude-fable-5-1", "claude-mythos-5", "claude-mythos-5-1",
            "claude-mythos-preview"}
DISABLE = MANUAL | {"claude-opus-4-7", "claude-opus-4-8", "claude-opus-5", "claude-sonnet-5"}
XHIGH = ADAPTIVE - {"claude-opus-4-6", "claude-sonnet-4-6", "claude-mythos-preview"}


def anthropic_options(settings):
    """No guessed modes, budget increases, effort substitutes or provider retries."""
    model = settings.model
    effort = settings.reasoning_effort or settings.reasoning
    budget = settings.thinking_budget
    # Capability exceptions only: unknown IDs are validated by the upstream API.
    known = model in MANUAL or model in ADAPTIVE
    options = {}
    if effort not in {"none", "low", "medium", "high", "max", "xhigh"}:
        raise ValueError("unsupported Claude effort value")
    if budget is not None:
        if (known and model not in MANUAL and model != "claude-mythos-preview") or not 1024 <= budget < settings.max_output_tokens:
            raise ValueError("Claude THINKING_BUDGET incompatible with model or outside 1024 <= budget < MAX_OUTPUT_TOKENS")
        options["thinking"] = {"type": "enabled", "budget_tokens": budget}
        if effort != "none":
            # Extended-only Haiku/Sonnet 4.5 lack effort; Opus 4.5 has three levels.
            opus45 = {"claude-opus-4-5", "claude-opus-4-5-20251101"}
            if (model in MANUAL - ADAPTIVE - opus45 or
                    model in opus45 and effort not in {"low", "medium", "high"} or
                    known and effort == "xhigh" and model not in XHIGH):
                raise ValueError("unsupported Claude effort with manual THINKING_BUDGET")
            options["output_config"] = {"effort": effort}
    elif effort != "none":
        if known and (model not in ADAPTIVE or (effort == "xhigh" and model not in XHIGH)):
            raise ValueError("unsupported Claude adaptive REASONING; manual models require THINKING_BUDGET")
        options = {"thinking": {"type": "adaptive"}, "output_config": {"effort": effort}}
    elif model in DISABLE:
        options["thinking"] = {"type": "disabled"}
    elif model == "claude-sonnet-5-5":
        # Native up-front off mode; no tools are requested by this text adapter.
        options["thinking"] = {"type": "between_tools"}
    # Always-on and unknown models retain their native default, with no invented off.
    if settings.temperature is not None:
        if (known and model not in MANUAL and settings.temperature != 1) or not 0 <= settings.temperature <= 1 or (options.get("thinking", {}).get("type") in {"enabled", "adaptive"} and settings.temperature != 1):
            raise ValueError("incompatible Claude TEMPERATURE/model combination; thinking permits only 1")
        options["temperature"] = settings.temperature
    return options


class AnthropicProvider:
    label = "Claude"
    API_BASE = "https://api.anthropic.com/v1"

    def __init__(self, *, api_key, model, instructions, client=None,
                 max_output_tokens=1024, model_options=None):
        self.client = client if client is not None else make_http_client()
        self.api_key, self.model = api_key, model
        self.instructions = provider_instructions(instructions)
        self.max_output_tokens = max_output_tokens
        self.model_options = model_options or {}

    async def stream(self, messages):
        try:
            system, history = [self.instructions], []
            for message in wire_messages(messages):
                if message["role"] == "system":
                    system.append(message["content"])
                else:
                    history.append(message)
            payload = {"model": self.model, "system": "\n\n".join(system),
                       "messages": history, "stream": True,
                       "max_tokens": self.max_output_tokens, **self.model_options}
            headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
            started = stopped = finished = False
            block = None
            index = -1
            token_filter = ExactTokenFilter()
            async with self.client.stream("POST", self.API_BASE + "/messages", headers=headers, json=payload) as response:
                if response.status_code == 529:  # Anthropic overload, not a new wire code.
                    raise provider_error(503)
                response.raise_for_status()
                async for event in sse_events(response):
                    kind = event.get("type")
                    if kind == "error":
                        code = event.get("error", {}).get("type")
                        status = {"authentication_error": 401, "permission_error": 403,
                                  "not_found_error": 404, "rate_limit_error": 429,
                                  "overloaded_error": 503}.get(code)
                        raise provider_error(status, code)
                    if kind == "ping":
                        continue
                    if finished:
                        raise ProviderError()
                    if kind == "message_start":
                        message = event.get("message", {})
                        if started or message.get("role") != "assistant" or message.get("content") != [] or message.get("stop_reason") is not None:
                            raise ProviderError()
                        started = True
                    elif kind == "content_block_start":
                        if not started or stopped or block is not None or type(event.get("index")) is not int or event["index"] != index + 1:
                            raise ProviderError()
                        index = event["index"]
                        content = event.get("content_block", {})
                        block = content.get("type")
                        if block not in {"text", "thinking", "redacted_thinking"}:
                            raise ProviderError()  # No tools, uploads or multimodal output.
                        if block == "text":
                            text = content.get("text")
                            if not isinstance(text, str):
                                raise ProviderError()
                            part = token_filter.feed(text)
                            if part:
                                yield part
                    elif kind == "content_block_delta":
                        if block is None or stopped or type(event.get("index")) is not int or event["index"] != index:
                            raise ProviderError()
                        delta = event.get("delta", {})
                        if block == "text" and delta.get("type") == "text_delta":
                            text = delta.get("text")
                            if not isinstance(text, str):
                                raise ProviderError()
                            part = token_filter.feed(text)
                            if part:
                                yield part
                        elif not (block == "thinking" and delta.get("type") in {"thinking_delta", "signature_delta"} or block == "text" and delta.get("type") == "citations_delta"):
                            raise ProviderError()
                    elif kind == "content_block_stop":
                        if block is None or type(event.get("index")) is not int or event["index"] != index:
                            raise ProviderError()
                        block = None
                    elif kind == "message_delta":
                        reason = event.get("delta", {}).get("stop_reason")
                        if not started or block is not None or stopped:
                            raise ProviderError()
                        if reason is not None:
                            if reason != "end_turn":
                                raise ProviderError()
                            stopped = True
                    elif kind == "message_stop":
                        if not stopped or block is not None or index < 0:
                            raise ProviderError()
                        finished = True
                    # Future metadata event types may be ignored, never counted as completion.
                if not finished:
                    raise ProviderError()
                final = token_filter.finish()
                if final:
                    yield final
        except Exception as exc:
            raise classify_error(exc) from None

    async def close(self):
        await self.client.aclose()
