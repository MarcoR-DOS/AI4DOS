"""Native Gemini text streaming, migrated from Georgi without private contexts."""
from urllib.parse import quote
from .provider import (ProviderError, classify_error, make_http_client,
                       provider_error, provider_instructions, wire_messages, sse_events)
from .textfilter import ExactTokenFilter


class GeminiProvider:
    label = "Gemini"
    API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, *, api_key, model, instructions, client=None,
                 temperature=0.5, max_output_tokens=1024,
                 thinking_level=None, thinking_budget=None):
        self.client = client if client is not None else make_http_client()
        self.api_key, self.model = api_key, model
        self.instructions = provider_instructions(instructions)
        self.temperature, self.max_output_tokens = temperature, max_output_tokens
        # Thinking is opt-in; no automatic low/minimal substitution.
        self.thinking_level = thinking_level
        self.thinking_budget = thinking_budget

    async def stream(self, messages):
        try:
            system = [self.instructions]
            contents = []
            for message in wire_messages(messages):
                if message["role"] == "system":
                    system.append(message["content"])
                else:
                    contents.append({"role": "model" if message["role"] == "assistant" else "user",
                                     "parts": [{"text": message["content"]}]})
            generation = {"temperature": self.temperature, "maxOutputTokens": self.max_output_tokens}
            if self.thinking_level is not None:
                generation["thinkingConfig"] = {"thinkingLevel": self.thinking_level.upper()}
            elif self.thinking_budget is not None:
                generation["thinkingConfig"] = {"thinkingBudget": self.thinking_budget}
            payload = {"systemInstruction": {"parts": [{"text": "\n\n".join(system)}]},
                       "contents": contents, "generationConfig": generation}
            url = self.API_BASE + "/" + quote(self.model, safe="-._") + ":streamGenerateContent?alt=sse"
            completed = False
            token_filter = ExactTokenFilter()
            async with self.client.stream("POST", url, headers={"x-goog-api-key": self.api_key}, json=payload) as response:
                response.raise_for_status()
                async for event in sse_events(response):
                    if "error" in event:
                        error = event["error"]
                        code = error.get("code") if isinstance(error, dict) else None
                        raise provider_error(code if isinstance(code, int) else None, code)
                    if event.get("promptFeedback", {}).get("blockReason"):
                        raise ProviderError()
                    candidates = event.get("candidates", [])
                    if not candidates:  # Usage/metadata is not a successful completion.
                        continue
                    if len(candidates) != 1 or candidates[0].get("index", 0) != 0:
                        raise ProviderError()
                    candidate = candidates[0]
                    for part in candidate.get("content", {}).get("parts", []):
                        if part.get("thought", False):
                            continue
                        text = part.get("text")
                        if text is None or not isinstance(text, str) or completed:
                            raise ProviderError()  # Images/tools are not a text response.
                        filtered = token_filter.feed(text)
                        if filtered:
                            yield filtered
                    reason = candidate.get("finishReason")
                    if reason:
                        if completed or reason != "STOP":
                            raise ProviderError()
                        completed = True
                if not completed:
                    raise ProviderError()
                final = token_filter.finish()
                if final:
                    yield final
        except Exception as exc:
            raise classify_error(exc) from None

    async def close(self):
        await self.client.aclose()
