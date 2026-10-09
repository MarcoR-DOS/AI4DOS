
from .textfilter import ExactTokenFilter
from .provider import ProviderError, classify_error, make_client, wire_messages, provider_instructions, provider_error


class OpenAIProvider:
    def __init__(self, *, api_key=None, model, instructions, client=None, base_url="https://api.openai.com/v1", label="ChatGPT", reasoning_effort=None, max_output_tokens=1024):
        if client is None:
            client = make_client(api_key, base_url)
        self.client = client
        self.model, self.instructions = model, provider_instructions(instructions)
        self.max_output_tokens = max_output_tokens
        self.label, self.reasoning_effort = label, reasoning_effort

    async def stream(self, messages):
        stream = self._stream(messages)
        try:
            async for part in stream:
                yield part
        except ProviderError:
            raise
        except Exception as exc:
            raise classify_error(exc) from None
        finally:
            await stream.aclose()

    async def _stream(self, messages):
        options = {} if self.reasoning_effort is None else {"reasoning": {"effort": self.reasoning_effort}}
        stream = await self.client.responses.create(
            model=self.model, instructions=self.instructions,
            input=wire_messages(messages),
            stream=True, store=False, max_output_tokens=self.max_output_tokens, **options,
        )
        completed = False
        token_filter = ExactTokenFilter()
        try:
            async for event in stream:
                if event.type == "response.output_text.delta":
                    if completed:
                        raise ProviderError()
                    part = token_filter.feed(event.delta)
                    if part:
                        yield part
                elif event.type == "response.completed":
                    if completed or getattr(getattr(event, "response", None), "status", "completed") != "completed":
                        raise ProviderError()
                    completed = True
                elif event.type == "error":
                    raise provider_error(code=getattr(event, "code", None))
                elif event.type == "response.failed":
                    error = getattr(getattr(event, "response", None), "error", None)
                    raise provider_error(code=getattr(error, "code", None))
                elif event.type == "response.incomplete":
                    raise ProviderError("UPSTREAM")
            if not completed:
                raise ProviderError("UPSTREAM")
            final = token_filter.finish()
            if final:
                yield final
        finally:
            await stream.close()

    async def close(self):
        await self.client.close()
