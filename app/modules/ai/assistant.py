"""One request to the assistant: ask the provider, check and repair what came back, and fall back to the stand-in's
answer when the provider fails or its answer can't be made valid (logged with the reason; the request keeps it)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from app.modules.ai.checks import OutputInvalid
from app.modules.ai.provider import ModelTask, ProviderError, get_provider
from app.modules.ai.service import Made

log = logging.getLogger("formalie.ai")


async def produce(task: ModelTask, convert: Callable[[Any], Any]) -> tuple[Any, Made]:
    """The answer in its final shape, and what made it."""
    provider = get_provider()
    try:
        reply = await provider.complete(task)
    except ProviderError as error:
        log.warning("AI provider gave no answer; the built-in assistant answered",
                    extra={"ai_task": task.task, "reason": error.reason})
        return task.standin(), Made("fallback", None, error.reason, error.usage)
    except Exception:  # noqa: BLE001  (a provider bug must never take the page down)
        log.exception("AI provider failed; the built-in assistant answered", extra={"ai_task": task.task})
        return task.standin(), Made("fallback", None, "provider_error")
    if reply.engine != "model":
        return reply.data, Made("standin", None, None, reply.usage)
    try:
        return convert(reply.data), Made("model", reply.model, None, reply.usage)
    except OutputInvalid as error:
        reason = f"invalid_{error.reason}"[:40]
    except Exception:  # noqa: BLE001  (an answer shaped in a way the checks didn't expect)
        log.exception("AI answer could not be read", extra={"ai_task": task.task})
        reason = "invalid"
    log.error("AI model answer could not be made valid; the built-in assistant answered",
              extra={"ai_task": task.task, "reason": reason, "model": reply.model})
    return task.standin(), Made("fallback", reply.model, reason, reply.usage)


async def produce_all(jobs: list[tuple[ModelTask, Callable[[Any], Any]]], limit: int = 4) -> tuple[list[Any], Made]:
    """Several requests at once (at most `limit` at a time), their answers in order and what made them together."""
    gate = asyncio.Semaphore(limit)

    async def one(task: ModelTask, convert: Callable[[Any], Any]) -> tuple[Any, Made]:
        async with gate:
            return await produce(task, convert)
    results = await asyncio.gather(*(one(t, c) for t, c in jobs))
    made = Made()
    for _, part in results:
        made.join(part)
    return [value for value, _ in results], made
