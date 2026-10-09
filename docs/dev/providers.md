# Provider adapters

[Developer index](README.md) · [Gateway](gateway.md) · [Release process](release-process.md)

## Contract and selection

[Provider](../../server/src/ai4dos/provider.py) defines `model`, `label`,
`stream(messages) -> AsyncIterator[str]` and asynchronous `close()`. Adapters yield
visible text only, validate terminal success and release their HTTP stream/client.
Gateway cancellation/response cleanup closes the generator. Errors crossing the
boundary must be `ProviderError` with fixed, public-safe codes and messages.

[config.py](../../server/src/ai4dos/config.py) contains `PRESETS`, validation,
`build_provider()` and reasoning selection. Provider IDs are a finite configured
set; **model IDs have no global allowlist**. Non-mock models must be nonempty and
contain no whitespace/DEL; OpenRouter alone supplies `openrouter/free` when empty.
Known-model sets select capability exceptions, not universal access permission.
Unknown IDs pass to the upstream service, which decides availability and options.

| Config ID | Adapter/API route | Visible label |
| --- | --- | --- |
| `openai` | [OpenAIProvider](../../server/src/ai4dos/openai_provider.py), Responses API | ChatGPT |
| `anthropic` | [AnthropicProvider](../../server/src/ai4dos/anthropic_provider.py), native Messages SSE | Claude |
| `gemini` | [GeminiProvider](../../server/src/ai4dos/gemini_provider.py), native streamGenerateContent SSE | Gemini |
| `mistral` | [CompatibleProvider](../../server/src/ai4dos/compatible_provider.py), Chat Completions | Mistral |
| `nvidia` | CompatibleProvider, Chat Completions | NVIDIA |
| `openrouter` | CompatibleProvider, Chat Completions | OpenRouter |
| `openai-compatible` | CompatibleProvider/chat or OpenAIProvider/responses, custom API root | AI/KI fallback |
| `mock` | [MockProvider](../../server/src/ai4dos/provider.py), deterministic local text | AI/KI fallback |

Only fixed known labels cross `BEGIN`; mock/compatible use a bare BEGIN and the
client's EN/DE AI/KI fallback. Labels are not model IDs, roles or session identity.
Custom BASE_URL is allowed only for `openai-compatible` (HTTP(S) root, no embedded
credentials/query/fragment); `API_MODE` is `chat` or `responses` there. Official
presets retain their selected API mode and root. Mock returns `Test reply: `,
the last message text and a newline, without API credentials.

## Reasoning and thinking

The global default `REASONING=none` expresses an intent to avoid opting into extra
reasoning/cost. It is **not** a universal guarantee that a model disables internal
thinking. The code does not silently substitute low/minimal, increase budgets,
change models or retry with another option. Explicit API-specific fields assert
capability and may be rejected by configuration or by the service.

| Route | Current mapping |
| --- | --- |
| OpenAI Responses | Explicit REASONING_EFFORT wins; otherwise non-none REASONING becomes `reasoning.effort`. Automatic `none` is sent only for official `gpt-6-luna`, `gpt-6-sol`, `gpt-5.1`; other IDs omit it. Responses uses `store=False`, max_output_tokens, no temperature. |
| OpenRouter | none sends `reasoning.enabled=false`; opt-in sends `reasoning.effort`. Explicit effort takes precedence. |
| Mistral | `mistral-small-latest`/`mistral-medium-3-5` accept mapped none/high only. Other IDs receive explicit effort or non-none reasoning; default none otherwise omits the parameter. |
| NVIDIA | `z-ai/glm-5.3` defaults `chat_template_kwargs.clear_thinking=true`; `nvidia/nemotron-3-super-120b-a12b` defaults enable_thinking=false. No automatic low effort for DeepSeek/GLM. Explicit flags override defaults; explicit effort/non-none reasoning is forwarded. Default temperature is 0.5. |
| openai-compatible | Chat forwards explicit effort/non-none reasoning; default none omits it. Responses uses the Responses mapping without official OpenAI automatic-off exceptions. |
| Gemini | Explicit THINKING_LEVEL or THINKING_BUDGET wins; they are mutually exclusive. Known 2.5 Flash/Flash-Lite and two Flash preview IDs map none to thinkingBudget=0. Other IDs omit the off parameter. Non-none 2.5 requires explicit budget; other opt-in levels are minimal/low/medium/high. Default temperature is 0.5. |
| Anthropic | `anthropic_options()` uses MANUAL/ADAPTIVE/DISABLE/XHIGH capability sets. Known disable-capable IDs get disabled with none; `claude-sonnet-5-5` gets between_tools. Always-on/unknown defaults are retained. Explicit manual budget requires 1024 <= budget < MAX_OUTPUT_TOKENS; adaptive effort and temperature restrictions are checked without inventing replacements. |
| mock | No model reasoning or external request. |

The exact model sets and edge-case precedence remain source-owned in
[config.py](../../server/src/ai4dos/config.py) and
[anthropic_options](../../server/src/ai4dos/anthropic_provider.py).
For example, an explicit Claude budget can enable thinking even while global
REASONING is none. These tables describe local payload construction, not current
provider promises for every model name.

## Text streams must complete

- **Responses:** visible output_text deltas are filtered; one successful
  response.completed is required. `error` and `response.failed` preserve their
  safe error category. Incomplete, duplicate completion and text after completion
  fail. Reasoning events are not DOS text.
- **Chat Completions:** one choice at index zero, textual content and final `stop`
  are required. Empty usage/metadata events alone do not complete a stream.
  Length/filter/error/tool finishes, tools and premature EOF fail.
- **OpenRouter final usage:** after a successful stop, one content-free choice
  repeating stop with usage is accepted. Late text and further invalid terminals
  still fail; this exception must not weaken completion checks for other labels.
- **Mistral blocks:** content lists may contain text blocks and, only for the
  Mistral label, structurally valid thinking lists containing text blocks.
  Thinking is discarded; visible text is yielded. Invalid lists/nontext output
  remain errors, including content after completion.
- **Gemini:** native SSE supports multiline data and a final record at EOF. One
  candidate at index zero and `STOP` are required. Thought parts are skipped;
  prompt blocks, tools/images, invalid text and unsuccessful finish reasons fail.
- **Claude:** message/block ordering and indexes are validated; text is yielded,
  thinking/signatures/redacted thinking remain hidden. Success requires end_turn
  followed by message_stop. Tool blocks, malformed sequencing and truncation fail.

[ExactTokenFilter](../../server/src/ai4dos/textfilter.py) removes two known exact
suffix tokens even across delta boundaries; it is not a general reasoning parser.
A stream ending without visible text fails at the gateway even if its adapter
observed a valid terminal. Usage records are not displayed or stored as chat text.

## Safe errors

[provider_error/classify_error](../../server/src/ai4dos/provider.py) deliberately
ignore raw upstream messages, URLs, request bodies and response bodies as public
text. Only machine-readable categories/statuses select fixed output:

| Wire category | Examples of classification |
| --- | --- |
| UPSTREAM_AUTH | 401/403, invalid_api_key, authentication_error |
| UPSTREAM_MODEL | 404, model_not_found/invalid_model/unknown_model; supported 400 model-param detection |
| UPSTREAM_RATE_LIMIT | 429, rate_limit_exceeded/rate_limit_error |
| UPSTREAM_UNAVAILABLE | connection/timeout/HTTP transport failures; 408/502/503/504; service_unavailable/connection_error; Claude overload 529 mapped to 503 |
| UPSTREAM | Other errors, including 402/500, incomplete or invalid text streams |

Typed ProviderError survives normalization. A model error without recognized
machine-readable evidence remains generic. No error frame is followed by a fake
END, and failed turns do not become successful session history.

## Validation evidence and its limits

These are historical scope statements, not fresh live checks by this documentation:

| Provider | Evidence available for this documentation |
| --- | --- |
| OpenAI | Previously recorded LIVE PASS with gpt-6-luna; offline regression coverage |
| NVIDIA | Previously recorded LIVE PASS with nvidia/nemotron-3-super-120b-a12b; offline option/stream coverage |
| OpenRouter | Previously recorded LIVE PASS with openrouter/free; offline final-usage regression |
| Gemini | Maintainer-reported successful real IBM XT validation with **gemini-3.5-flash-lite** (2026-10-08); not an automated live check. **gemini-2.5-flash** is not live confirmed. |
| Anthropic/Claude | Implemented and OFFLINE/contract validated; no live validation confirmed |
| Mistral | Implemented and OFFLINE/contract validated; no live validation confirmed |
| openai-compatible/mock | Offline contracts/local mock behavior; no blanket external live support guarantee |

A default gate labels unrequested live checks LIVE NOT AVAILABLE (`not requested`).
Gemini's hardware success applies only to the reported successful model; it does
not certify gemini-2.5-flash, all Gemini models or the latest packaged DOS build.
Claude/Mistral remain offline validated unless an explicit live run is performed
with an available key and recorded evidence. Model availability is upstream-specific.

## Adding a provider

1. Implement the async text/close contract, explicit completion, cancellation
   cleanup, safe errors and capability/language instructions; reuse shared helpers.
2. Add configuration ID/preset, factory construction, key source and option
   validation. Keep arbitrary model IDs separate from capability exceptions.
3. If a new visible label is intentional, update the gateway label filter and
   client protocol label recognition, plus label tests and the separate protocol
   document when its contract changes. Roles and history must remain independent.
4. Add synthetic HTTP/SSE/SDK tests for request mapping, thinking suppression,
   success/usage, incomplete streams, errors and cleanup. Add a regression fixture
   for the actual failure; never capture real credentials.
5. Update explicit module packaging in `tools/package-release.py` if adding a
   module, and provider/suite coverage in `tools/validate-release.py`. Include the
   change in the [release gate](release-process.md#mandatory-offline-gate).
6. Report offline evidence separately from explicitly authorized live evidence;
   update documentation and reviewed config hints as needed within approved scope.
