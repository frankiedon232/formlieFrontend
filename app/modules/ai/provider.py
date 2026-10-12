"""Who answers the assistant's requests (owner, 2026-10-12: Anthropic Claude).

A `ModelTask` is one request to a model: stable instructions (`system`, cached by the provider), the request itself
(`content`, JSON text), the JSON schema the answer must follow, which model (the main one, or the lighter one for quick
tasks) and the stand-in's own answer (`standin`, the mock's local engines, already in the final shape).

- `AnthropicProvider` calls the Messages API with the official `anthropic` SDK: structured output
  (`output_config.format` json_schema, so the answer is JSON in that shape), the system prompt marked for prompt
  caching, the SDK's timeout and retries (connection errors, 429, 5xx), and Anthropic's recommended fallback model
  when Opus or Sonnet declines (`fallbacks: "default"`). Any failure raises `ProviderError` with a short reason.
- `StandInProvider` answers with the stand-in: used when no key is set (development, tests), so the portal works
  without one. Tests never reach the internet: in the test environment the stand-in is used unless a test sets its
  own provider (`use_provider`).

Whatever a model returns is checked and repaired by app/modules/ai/checks.py before anyone sees it; output that can't
be made valid falls back to the stand-in's answer, and the request records why (`fallback_reason`).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from app.core.config import get_settings

log = logging.getLogger("formalie.ai")


@dataclass
class ModelTask:
    task: str  # what it is for (form_draft, theme_draft, assist, translate, rewrite, labels, question, summary)
    system: str
    content: str
    schema: dict[str, Any]
    standin: Callable[[], Any]
    fast: bool = False
    max_tokens: int = 16_000


@dataclass
class Usage:
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def add(self, other: Usage) -> None:
        self.model_calls += other.model_calls
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_read_tokens += other.cache_read_tokens
        self.cache_write_tokens += other.cache_write_tokens


@dataclass
class ModelReply:
    data: Any
    engine: str  # model · standin
    model: str | None = None
    usage: Usage = field(default_factory=Usage)


class ProviderError(Exception):
    """The provider gave no usable answer: `reason` is short and safe to keep (never the key or the content)."""

    def __init__(self, reason: str, usage: Usage | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.usage = usage or Usage()


class AiProvider(Protocol):
    name: str

    async def complete(self, task: ModelTask) -> ModelReply: ...


class StandInProvider:
    """The built-in engines (the mock's), no outside service."""

    name = "standin"

    async def complete(self, task: ModelTask) -> ModelReply:
        return ModelReply(task.standin(), "standin")


_SAFE_FALLBACK_FAMILIES = ("claude-opus", "claude-sonnet", "claude-fable")


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str, fast_model: str, timeout: float, max_retries: int,
                 fallbacks: bool) -> None:
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=max_retries)
        self.model, self.fast_model, self.fallbacks = model, fast_model, fallbacks

    def _usage(self, response: Any) -> Usage:
        usage = getattr(response, "usage", None)
        if usage is None:
            return Usage(model_calls=1)
        # With a fallback, every attempt is listed (`iterations`); otherwise the top level is the only one
        parts = [p for p in (getattr(usage, "iterations", None) or []) if p is not None] or [usage]
        total = Usage(model_calls=1)
        for part in parts:
            total.input_tokens += int(getattr(part, "input_tokens", 0) or 0)
            total.output_tokens += int(getattr(part, "output_tokens", 0) or 0)
            total.cache_read_tokens += int(getattr(part, "cache_read_input_tokens", 0) or 0)
            total.cache_write_tokens += int(getattr(part, "cache_creation_input_tokens", 0) or 0)
        return total

    async def complete(self, task: ModelTask) -> ModelReply:
        a = self._anthropic
        model = self.fast_model if task.fast else self.model
        request: dict[str, Any] = {
            "model": model,
            "max_tokens": task.max_tokens,
            "system": [{"type": "text", "text": task.system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": task.content}],
            "output_config": {"effort": "low" if task.fast else "medium",
                              "format": {"type": "json_schema", "schema": task.schema}},
        }
        try:
            if self.fallbacks and model.startswith(_SAFE_FALLBACK_FAMILIES):
                response = await self.client.beta.messages.create(
                    **request, betas=["server-side-fallback-2026-07-01"], fallbacks="default")
            else:
                response = await self.client.messages.create(**request)
        except a.AuthenticationError:
            raise ProviderError("credentials") from None
        except a.PermissionDeniedError:
            raise ProviderError("permission") from None
        except a.RateLimitError:
            raise ProviderError("rate_limited") from None
        except a.BadRequestError as error:
            log.error("AI provider refused the request", extra={"task": task.task, "status": 400,
                                                                 "provider_message": str(error.message)[:300]})
            raise ProviderError("bad_request") from None
        except a.APITimeoutError:
            raise ProviderError("timeout") from None
        except a.APIConnectionError:
            raise ProviderError("unreachable") from None
        except a.APIStatusError as error:
            raise ProviderError(f"status_{error.status_code}") from None
        usage = self._usage(response)
        if response.stop_reason == "refusal":
            raise ProviderError("refused", usage)
        if response.stop_reason == "max_tokens":
            raise ProviderError("cut_off", usage)
        text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), None)
        if text is None:
            raise ProviderError("empty", usage)
        try:
            data = json.loads(text)
        except ValueError:
            raise ProviderError("not_json", usage) from None
        return ModelReply(data, "model", getattr(response, "model", None) or model, usage)


_override: AiProvider | None = None
_cached: AiProvider | None = None


def use_provider(provider: AiProvider | None) -> None:
    """Tests (and scripts) pick the provider; None goes back to the settings."""
    global _override
    _override = provider


def get_provider() -> AiProvider:
    global _cached
    if _override is not None:
        return _override
    settings = get_settings()
    key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else ""
    if not key or settings.app_env == "test":
        return StandInProvider()
    if _cached is None:
        _cached = AnthropicProvider(key, settings.anthropic_model, settings.anthropic_fast_model,
                                    settings.anthropic_timeout_seconds, settings.anthropic_max_retries,
                                    settings.anthropic_fallbacks)
    return _cached
