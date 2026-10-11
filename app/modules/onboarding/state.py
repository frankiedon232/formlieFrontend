"""The onboarding state a workspace starts with (kept with its settings, section `onboarding`)."""

from __future__ import annotations

from typing import Any

from app.modules.settings.catalogues import ONBOARDING_STEPS

SECTION = "onboarding"


def new_state() -> dict[str, Any]:
    """A workspace made by sign-up starts at the first step."""
    return {"status": "not_started", "current_step": "company", "steps": {s: "todo" for s in ONBOARDING_STEPS},
            "invites": [], "first_form": {"choice": None, "template_key": None}}


def set_up_state() -> dict[str, Any]:
    """No onboarding row (the seeded workspaces, and any from before onboarding was built): already set up."""
    return {**new_state(), "status": "completed", "steps": {s: "done" for s in ONBOARDING_STEPS}}
