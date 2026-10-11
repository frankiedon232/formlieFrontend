"""What a submission hands to the `notifications` queue in tests (emails, notifications), kept until a test runs it.
Its own module, so the conftest fixture and the tests share one list."""

from __future__ import annotations

AFTER_SUBMIT: list[tuple] = []


async def run_after_submit() -> None:
    from app.modules.responses.after import after_submit

    while AFTER_SUBMIT:
        await after_submit(*AFTER_SUBMIT.pop(0))
