# Configure providers and models

## 1. Set up API access

You need separate API access and an API key from your chosen provider. A regular ChatGPT, Claude or Gemini subscription is **not API access**; signing in to the website or app is not enough.

For an easy start, we recommend **OpenRouter**. The service offers access to different models through one API account, including free options. The template uses `PROVIDER=openrouter` and `MODEL=openrouter/free`. Create an OpenRouter API key and enter it on the gateway. OpenRouter determines which free models and allowances are available; this guide does not maintain a fixed model list.

## 2. Enter the provider on the gateway

Open the provider file with a plain text editor:

- Windows, macOS and Linux: `server/provider.local.cfg`
- Docker / Portainer: `config.local/provider.cfg`

Choose one provider and use its value exactly:

| Provider | Value for `PROVIDER=` |
| --- | --- |
| OpenAI / ChatGPT | `openai` |
| Anthropic / Claude | `anthropic` |
| Google Gemini | `gemini` |
| Mistral | `mistral` |
| NVIDIA | `nvidia` |
| OpenRouter | `openrouter` |
| OpenAI-compatible APIs | `openai-compatible` |

Example:

```ini
PROVIDER=openrouter
```

Choose **one** value and keep only one `PROVIDER=` line in the file. `openai-compatible` is for an OpenAI-compatible API endpoint; also enter its `BASE_URL=`.

The **API key belongs exclusively on the gateway, never in `AI4DOS.CFG`**. In native packages, enter it at `API_KEY=` in `server/provider.local.cfg`. With Docker / Portainer, enter it at `API_KEY=` in `config.local/provider.cfg`.

## 3. Choose a model

AI4DOS does not maintain a fixed model list. Enter the model ID at `MODEL=` exactly as specified by the respective API provider. Get the exact model name from that provider’s API/developer documentation.

The provider decides whether the model ID is available and enabled for your API account.

For an easy free start with OpenRouter, you can initially leave the prepared default `MODEL=openrouter/free` unchanged. OpenRouter can then select a currently available free model. If you later want to use a specific model, enter its model ID at `MODEL=`.

This does not guarantee that every model or special option works. This page is not a live model catalogue and does not confirm live validation of individual models.

## 4. Reasoning / Thinking

The global default is:

```ini
REASONING=none
```

AI4DOS therefore does not request an additional optional reasoning feature. This protects against automatically enabling modes that can consume more tokens and incur extra costs. It does not mean that internal thinking can be fully disabled for every model.

Keep the default when getting started. Provider- and model-specific thinking options can differ; enable them deliberately only after checking the relevant API and pricing information.

The AI4DOS configuration accepts these values; the model's API determines which it supports:

| Setting | Values | Applies to |
| --- | --- | --- |
| `REASONING` | `none` (default), `minimal`, `low`, `medium`, `high`, `xhigh`, `max` | General setting; the respective adapter maps it to the API. |
| `REASONING_EFFORT` | `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max` | OpenAI Responses, Anthropic, Mistral, NVIDIA, OpenRouter and OpenAI-compatible APIs; overrides `REASONING`. |
| `THINKING_LEVEL` | `minimal`, `low`, `medium`, `high` | Gemini only; overrides `REASONING` there. |
| `THINKING_BUDGET` | Gemini: integer from `-1`; Claude: `1024` to less than `MAX_OUTPUT_TOKENS` | Explicit thinking budget; can enable thinking even with `REASONING=none`. |

For Gemini, set only **one** of `THINKING_LEVEL` and `THINKING_BUDGET`. AI4DOS forwards the budget unchanged to the API; the model determines its meaning and supported range. Gemini 2.5 requires an explicit budget to enable thinking deliberately; without an override, Gemini accepts only `minimal`, `low`, `medium`, `high` as active reasoning levels. With `REASONING=none`, AI4DOS sets a budget of `0` for the known Gemini 2.5 Flash/Flash-Lite IDs; other IDs retain the API default.

Claude does not accept `minimal`. Models with manual thinking require `THINKING_BUDGET`; `MAX_OUTPUT_TOKENS` must exceed that budget. Adaptive models use an effort level without a manual budget; `xhigh` is limited to certain adaptive models. With a manual budget, Haiku/Sonnet 4.5 do not support an additional effort level, and Opus 4.5 supports only `low`, `medium`, `high`. For `mistral-small-latest` and `mistral-medium-3-5`, AI4DOS accepts only `none` or `high`.

OpenRouter maps `none` to `reasoning.enabled=false`. OpenAI sends the automatic value `none` only for the IDs recorded in the adapter: `gpt-6-luna`, `gpt-6-sol` and `gpt-5.1`; otherwise no effort value is sent without an override. NVIDIA also uses the model defaults recorded in the adapter. The complete technical mapping, including Claude and NVIDIA exceptions, is in the [developer documentation](../dev/providers.md#reasoning-and-thinking). Invalid combinations can prevent gateway startup or be rejected by the provider.

Explicit overrides can remain effective independently of `REASONING=none`. Remove them when returning to defaults.

Save changes and restart the gateway as described in your installation guide: [Windows](install-windows.md#change-settings-later), [macOS](install-macos.md#change-settings-later), [Linux](install-linux.md#change-settings-later) or [Docker / Portainer](install-docker.md#9-change-settings-later). See [Troubleshooting](troubleshooting.md) for help with errors.

## Reply length and transport

The default limits are suitable for getting started. To deliberately request shorter or longer replies, add `MAX_OUTPUT_TOKENS=` to the active provider file (default `1024`). The additional gateway limit `max_reply_bytes` belongs in the gateway JSON (default `65536` UTF-8 bytes). Save changes and restart the gateway. These limits are independent of DOS memory and [scrollback/transcript](dos-setup.md#use-the-dos-client). Larger replies are transferred in several small data blocks, not one huge network block.

`MAX_OUTPUT_TOKENS` must be a positive integer; AI4DOS imposes no fixed upper bound, but the provider does. Tokens do not correspond to a fixed number of characters or bytes. If the model ends incompletely because of the token limit, the adapters treat this as an `UPSTREAM` error rather than a complete reply.

If a reply exceeds `max_reply_bytes`, the gateway aborts with `UPSTREAM` (`response generation failed`). In normal DOS output mode, the reply is rendered and transferred only after complete reception, so no reply text arrives for this error. In UTF-8 output mode, previously transferred parts can remain visible. An interrupted reply and its new user message are not added to the gateway's model context.

The DOS transcript holds **61,440 bytes (60 KiB)** in total, including labels, line endings and internal record bookkeeping. At **51,200 bytes (50 KiB)**, “Transcript almost full” appears. If the remaining space is insufficient, “Transcript full” appears: the client displays and stores only the part of the reply that still fits and blocks further messages. Save with F5 and start a new chat with F2. How much of the next reply fits depends on the space already used. Increasing the gateway limit does not enlarge this storage; a reply completed by the gateway can remain complete in the model context even when its local display is shortened.

Official providers are accessed through HTTPS. An explicitly configured `openai-compatible` endpoint can also use HTTP. This does not change the unencrypted DOS↔gateway traffic.

## Offline function test without API access

With the built-in Mock provider, you can test AI4DOS without needing API access or an API key.

Open the provider configuration file (`server/provider.local.cfg`, or `config.local/provider.cfg` for Docker) and use the following settings:

```ini
PROVIDER=mock
MODEL=mock
API_KEY=
REASONING=none
```

**Important:** If you previously used another provider, remove its additional settings from the file or comment them out with `#` or `;`. The easiest option is to use a fresh copy of the supplied provider configuration for the test.

Then restart the gateway and send a message through AI4DOS. You will receive a reply that starts with `Test reply:` and repeats your message.

The normal device key and a working network connection between the DOS PC and the gateway are still required.
