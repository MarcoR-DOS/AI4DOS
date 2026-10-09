from dataclasses import dataclass, field
import json
import os
import math
from urllib.parse import urlsplit
from pathlib import Path
from .protocol import DEVICE_RE


# Transport/API details stay in provider construction, never in Gateway/session.
PRESETS = {
    "openai": ("https://api.openai.com/v1", "responses", "ChatGPT", "OPENAI_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "chat", "OpenRouter", "OPENROUTER_API_KEY"),
    "mistral": ("https://api.mistral.ai/v1", "chat", "Mistral", "MISTRAL_API_KEY"),
    "anthropic": ("https://api.anthropic.com/v1", "native", "Claude", "ANTHROPIC_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/models", "native", "Gemini", "GEMINI_API_KEY"),
    "nvidia": ("https://integrate.api.nvidia.com/v1", "chat", "NVIDIA", "NVIDIA_API_KEY"),
    "openai-compatible": ("", "chat", "AI", "API_KEY"),
}
PROVIDER_FIELDS = {"PROVIDER": "provider", "MODEL": "model", "API_KEY": "api_key",
                   "BASE_URL": "base_url", "API_MODE": "api_mode", "API_KEY_FILE": "api_key_file",
                   "REASONING": "reasoning", "REASONING_EFFORT": "reasoning_effort", "MAX_OUTPUT_TOKENS": "max_output_tokens",
                   "TEMPERATURE": "temperature", "THINKING_LEVEL": "thinking_level",
                   "THINKING_BUDGET": "thinking_budget", "ENABLE_THINKING": "enable_thinking",
                   "CLEAR_THINKING": "clear_thinking"}
OPTION_FIELDS = {"max_output_tokens", "temperature", "thinking_level", "thinking_budget",
                 "enable_thinking", "clear_thinking"}


class ConfigurationError(ValueError):
    """Reviewed startup text; never include configuration values or secrets."""


def config_value(name, value):
    if name in {"max_output_tokens", "thinking_budget"}:
        return int(value)
    if name == "temperature":
        return float(value)
    if name in {"enable_thinking", "clear_thinking"}:
        if value.lower() not in {"true", "false"}:
            raise ValueError("thinking flags must be true or false")
        return value.lower() == "true"
    return value


def read_provider_config(path):
    values = {}
    for row in Path(path).read_text(encoding="utf-8").splitlines():
        row = row.strip()
        if not row or row.startswith(("#", ";")):
            continue
        key, separator, value = row.partition("=")
        key = key.strip()
        if not separator or key not in PROVIDER_FIELDS or PROVIDER_FIELDS[key] in values:
            raise ValueError("invalid or duplicate provider config field")
        name = PROVIDER_FIELDS[key]
        values[name] = config_value(name, value.strip())
    return values


@dataclass
class Settings:
    host: str = "127.0.0.1"
    port: int = 1983
    devices: dict = field(default_factory=dict)
    provider: str = "mock"
    model: str = ""
    base_url: str = ""
    api_mode: str = ""
    api_key: str = field(default="", repr=False)
    api_key_file: str = field(default="", repr=False)
    reasoning: str = "none"
    reasoning_effort: str = None
    max_output_tokens: int = 1024
    temperature: float = None
    thinking_level: str = None
    thinking_budget: int = None
    enable_thinking: bool = None
    clear_thinking: bool = None
    output_mode: str = "dos"
    instructions: str = "Answer clearly in plain text."
    max_reply_bytes: int = 65536
    request_timeout: float = 120.0
    idle_timeout: float = 300.0
    auth_timeout: float = 30.0
    max_unauthenticated_connections: int = 16
    max_connections_per_device: int = 2
    session_ttl: float = 3600.0
    max_sessions_per_device: int = 32

    def __post_init__(self):
        if not isinstance(self.devices, dict) or not self.devices:
            raise ConfigurationError('Device configuration missing or empty. Set devices with a device ID and your own key (at least 8 characters).')
        for device, secret in self.devices.items():
            if not isinstance(device, str) or not DEVICE_RE.fullmatch(device) or not isinstance(secret, str):
                raise ConfigurationError("Invalid device configuration. Use a valid device ID and a string key.")
            if not 8 <= len(secret) <= 128 or any(not 33 <= ord(c) <= 126 for c in secret):
                raise ConfigurationError("Device key must be 8-128 printable ASCII characters without spaces. Set the same value as SECRET in AI4DOS.CFG.")
        if not isinstance(self.provider, str) or self.provider not in {"mock", *PRESETS}:
            raise ConfigurationError("Unknown provider. Choose a provider listed in the AI4DOS provider guide.")
        if self.output_mode not in {"dos", "utf8"}:
            raise ValueError("invalid output mode")
        if (type(self.auth_timeout) not in {int, float} or not math.isfinite(self.auth_timeout)
                or self.auth_timeout <= 0 or type(self.max_unauthenticated_connections) is not int
                or self.max_unauthenticated_connections < 1):
            raise ConfigurationError("Invalid pre-auth limits. Use a positive auth_timeout and integer max_unauthenticated_connections.")
        if not 0 <= self.port <= 65535 or self.max_reply_bytes < 1 or self.request_timeout <= 0 or self.idle_timeout <= 0 or self.max_connections_per_device < 1 or self.session_ttl <= 0 or self.max_sessions_per_device < 1:
            raise ValueError("invalid limits")
        if self.provider == "openrouter" and self.model == "":
            self.model = "openrouter/free"
        if self.provider != "mock" and not self.model:
            raise ConfigurationError("Model is missing. Set MODEL in the provider configuration.")
        if not isinstance(self.model, str) or any(c.isspace() or ord(c) == 127 for c in self.model):
            raise ConfigurationError("Model is invalid. Use a provider model ID without whitespace.")
        if self.provider == "openai-compatible":
            url = urlsplit(self.base_url)
            if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError("BASE_URL must be an HTTP(S) API root without credentials/query")
        elif self.base_url:
            raise ValueError("custom BASE_URL requires openai-compatible")
        expected_mode = PRESETS.get(self.provider, ("", "chat"))[1]
        if not self.api_mode:
            self.api_mode = expected_mode
        if self.api_mode not in {"chat", "responses", "native"} or (self.provider == "openai-compatible" and self.api_mode == "native") or (self.provider != "openai-compatible" and self.api_mode != expected_mode):
            raise ValueError("unsupported API_MODE for provider")
        if self.reasoning not in {"none", "minimal", "low", "medium", "high", "xhigh", "max"}:
            raise ValueError("invalid REASONING setting")
        if self.reasoning_effort is not None and (self.provider not in {"anthropic", "nvidia", "mistral", "openrouter", "openai-compatible"} and self.api_mode != "responses" or self.reasoning_effort not in {"none", "minimal", "low", "medium", "high", "xhigh", "max"}):
            raise ValueError("REASONING_EFFORT requires a reasoning-capable API")
        if type(self.max_output_tokens) is not int or self.max_output_tokens < 1:
            raise ValueError("MAX_OUTPUT_TOKENS must be a positive integer")
        if self.temperature is not None and (type(self.temperature) not in {int, float} or not math.isfinite(self.temperature) or not 0 <= self.temperature <= 2 or self.api_mode == "responses"):
            raise ValueError("unsupported TEMPERATURE")
        if self.thinking_level is not None and (self.provider != "gemini" or self.thinking_level not in {"minimal", "low", "medium", "high"}):
            raise ValueError("THINKING_LEVEL requires Gemini")
        if self.thinking_budget is not None and (self.provider not in {"gemini", "anthropic"} or type(self.thinking_budget) is not int or self.thinking_budget < -1):
            raise ValueError("THINKING_BUDGET requires Gemini/Anthropic and a supported integer")
        if self.thinking_level is not None and self.thinking_budget is not None:
            raise ValueError("choose THINKING_LEVEL or THINKING_BUDGET")
        for flag in (self.enable_thinking, self.clear_thinking):
            if flag is not None and (self.provider != "nvidia" or type(flag) is not bool):
                raise ValueError("thinking template flags require NVIDIA booleans")
        if self.provider == "anthropic":
            from .anthropic_provider import anthropic_options
            anthropic_options(self)
        elif self.provider == "gemini":
            gemini_thinking(self)
        elif self.api_mode == "chat":
            chat_reasoning(self)
        if not isinstance(self.api_key, str) or not isinstance(self.api_key_file, str):
            raise ValueError("invalid API key configuration")
        if self.api_key and self.api_key_file:
            raise ValueError("choose API_KEY or API_KEY_FILE")

    @classmethod
    def load(cls, path):
        path = Path(path)
        values = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(values, dict):
            raise ConfigurationError("Gateway config must be a JSON object.")
        provider_path = values.pop("provider_config", None)
        if provider_path:
            provider_path = path.parent / Path(provider_path).expanduser()
            options = read_provider_config(provider_path)
            # Provider file is authoritative; stale JSON provider secrets never win.
            for name in PROVIDER_FIELDS.values():
                if name not in OPTION_FIELDS:
                    values.pop(name, None)
            values.update(options)
        if values.get("api_key_file"):
            parent = provider_path.parent if provider_path else path.parent
            values["api_key_file"] = str(parent / Path(values["api_key_file"]).expanduser())
        return cls(**values)


def build_provider(settings):
    if settings.provider == "mock":
        from .provider import MockProvider
        return MockProvider()
    base, _, label, env_name = PRESETS[settings.provider]
    if settings.api_key_file:
        key = Path(settings.api_key_file).read_text(encoding="utf-8").strip()
    else:
        key = settings.api_key or os.environ.get(env_name) or os.environ.get("API_KEY")
    if not key:
        raise ConfigurationError("No API key configured. Set API_KEY in your active provider configuration file (see the AI4DOS installation guide).")
    if any(not 33 <= ord(c) <= 126 for c in key):
        raise ConfigurationError("API key is invalid. Check your local key configuration.")
    base = settings.base_url or base
    if settings.api_mode == "responses":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=key, base_url=base, model=settings.model,
                              instructions=settings.instructions, label=label,
                              reasoning_effort=responses_reasoning(settings),
                              max_output_tokens=settings.max_output_tokens)
    if settings.provider == "anthropic":
        from .anthropic_provider import AnthropicProvider, anthropic_options
        return AnthropicProvider(api_key=key, model=settings.model, instructions=settings.instructions,
                                 max_output_tokens=settings.max_output_tokens,
                                 model_options=anthropic_options(settings))
    if settings.provider == "gemini":
        from .gemini_provider import GeminiProvider
        return GeminiProvider(api_key=key, model=settings.model, instructions=settings.instructions,
                              max_output_tokens=settings.max_output_tokens,
                              temperature=0.5 if settings.temperature is None else settings.temperature,
                              thinking_level=gemini_thinking(settings)[0],
                              thinking_budget=gemini_thinking(settings)[1])
    from .compatible_provider import CompatibleProvider
    return CompatibleProvider(api_key=key, base_url=base, model=settings.model,
                              instructions=settings.instructions, label=label,
                              max_output_tokens=settings.max_output_tokens,
                              temperature=(0.5 if settings.provider == "nvidia" and settings.temperature is None else settings.temperature),
                              model_options=chat_reasoning(settings))


def responses_reasoning(settings):
    # Explicit API-specific configuration remains an opt-in/capability assertion.
    if settings.reasoning_effort is not None:
        return settings.reasoning_effort
    if settings.reasoning != "none":
        return settings.reasoning
    # Only known, supported official models receive an automatic off parameter.
    if settings.provider == "openai" and settings.model in {"gpt-6-luna", "gpt-6-sol", "gpt-5.1"}:
        return "none"
    return None


def gemini_thinking(settings):
    if settings.thinking_level is not None or settings.thinking_budget is not None:
        return settings.thinking_level, settings.thinking_budget
    if settings.reasoning != "none":
        if settings.model.startswith("gemini-2.5"):
            raise ValueError("Gemini 2.5 opt-in requires explicit THINKING_BUDGET")
        if settings.reasoning not in {"minimal", "low", "medium", "high"}:
            raise ValueError("unsupported Gemini REASONING level")
        return settings.reasoning, None
    # Gemini 3 and 2.5 Pro have no full off switch. Never substitute low/minimal.
    if settings.model in {"gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash-preview-04-17", "gemini-2.5-flash-preview-05-20"}:
        return None, 0
    return None, None


def nvidia_options(settings):
    """Preserve technical model defaults without implicitly opting into thinking."""
    options = {}
    if settings.model == "z-ai/glm-5.3":
        options["chat_template_kwargs"] = {"clear_thinking": True}
    elif settings.model == "nvidia/nemotron-3-super-120b-a12b":
        options["chat_template_kwargs"] = {"enable_thinking": False}
    # DeepSeek/GLM no longer receive Georgi's automatic reasoning_effort=low.
    effort = settings.reasoning_effort
    if effort is None and settings.reasoning != "none":
        effort = settings.reasoning
    if effort is not None:
        options["reasoning_effort"] = effort
    for name in ("enable_thinking", "clear_thinking"):
        value = getattr(settings, name)
        if value is not None:
            options.setdefault("chat_template_kwargs", {})[name] = value
    return options


def chat_reasoning(settings):
    if settings.provider == "nvidia":
        return nvidia_options(settings)
    effort = settings.reasoning_effort or settings.reasoning
    if settings.provider == "openrouter":
        return {"reasoning": {"enabled": False}} if effort == "none" else {"reasoning": {"effort": effort}}
    if settings.provider == "mistral":
        if settings.model in {"mistral-small-latest", "mistral-medium-3-5"}:
            if effort not in {"none", "high"}:
                raise ValueError("unsupported Mistral REASONING level")
            return {"reasoning_effort": effort}
        if settings.reasoning_effort is not None or effort != "none":
            return {"reasoning_effort": effort}
    if settings.provider == "openai-compatible":
        if settings.reasoning_effort is not None or effort != "none":
            return {"reasoning_effort": effort}
    return {}
