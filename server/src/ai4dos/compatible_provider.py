"""Text-only Chat Completions adapter shared by compatible provider presets."""
from .provider import ProviderError, classify_error, make_client, provider_error, wire_messages, provider_instructions
from .textfilter import ExactTokenFilter


class CompatibleProvider:
    def __init__(self, *, api_key=None, model, instructions, base_url, label="AI", client=None, max_output_tokens=1024, temperature=None, model_options=None):
        self.client = client if client is not None else make_client(api_key, base_url)
        self.model, self.instructions, self.label = model, provider_instructions(instructions), label
        self.max_output_tokens, self.temperature = max_output_tokens, temperature
        self.model_options = model_options or {}

    async def stream(self, messages):
        stream = None
        completed = False
        usage_completed = False
        token_filter = ExactTokenFilter()
        try:
            request = wire_messages(messages)
            if self.instructions:
                request.insert(0, {"role": "system", "content": self.instructions})
            options = {}
            if self.temperature is not None:
                options["temperature"] = self.temperature
            if self.model_options:
                options["extra_body"] = self.model_options
            stream = await self.client.chat.completions.create(
                model=self.model, messages=request, stream=True, max_tokens=self.max_output_tokens, **options,
            )
            async for chunk in stream:
                error = getattr(chunk, "error", None)
                if error:
                    code = error.get("code") if isinstance(error, dict) else None
                    raise provider_error(code if isinstance(code, int) else None, code)
                choices = getattr(chunk, "choices", None)
                if not choices:  # Empty usage/metadata event, not completion.
                    continue
                if len(choices) != 1 or choices[0].index != 0:
                    raise ProviderError()
                choice = choices[0]
                delta = choice.delta
                if getattr(delta, "tool_calls", None) or getattr(delta, "function_call", None):
                    raise ProviderError()  # Gateway is text-only; no tool execution.
                content = getattr(delta, "content", None)
                if isinstance(content, list):  # Mistral thinking/text-block representation.
                    if completed and content:
                        raise ProviderError()
                    texts = []
                    for block in content:
                        if not isinstance(block, dict):
                            raise ProviderError()
                        if block.get("type") == "text" and isinstance(block.get("text"), str):
                            texts.append(block["text"])
                        elif self.label == "Mistral" and block.get("type") == "thinking":
                            thinking = block.get("thinking")
                            if not isinstance(thinking, list) or any(
                                    not isinstance(item, dict) or item.get("type") != "text"
                                    or not isinstance(item.get("text"), str) for item in thinking):
                                raise ProviderError()
                            # Internal reasoning is never DOS-visible output.
                        else:
                            raise ProviderError()
                    content = "".join(texts)
                if content:
                    if completed or not isinstance(content, str):
                        raise ProviderError()
                    part = token_filter.feed(content)
                    if part:
                        yield part
                # OpenRouter repeats stop in its final content-free usage choice.
                if (completed and self.label == "OpenRouter" and not usage_completed
                        and choice.finish_reason == "stop" and not content
                        and getattr(chunk, "usage", None) is not None):
                    usage_completed = True
                    continue
                if choice.finish_reason is not None:
                    if completed or choice.finish_reason != "stop":
                        raise ProviderError()  # length/filter/error/tool_calls are not success.
                    completed = True
            if not completed:
                raise ProviderError()  # EOF/[DONE] without a successful finish is incomplete.
            final = token_filter.finish()
            if final:
                yield final
        except Exception as exc:
            raise classify_error(exc) from None
        finally:
            if stream is not None:
                await stream.close()

    async def close(self):
        await self.client.close()
