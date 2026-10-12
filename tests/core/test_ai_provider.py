"""The AI provider and the checks on what a model returns (no internet: the SDK client is replaced by a fake).

- AnthropicProvider: the request it sends (cached system prompt, structured output, effort, Anthropic's recommended
  fallback for Opus but not Haiku), tokens counted across fallback attempts, and every failure as a short reason.
- The stand-in answers in tests and without a key.
- checks.py: good answers kept, bad ones repaired, broken ones refused (OutputInvalid), for every kind of task.
"""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import pytest

from app.core.config import get_settings
from app.modules.ai import checks as C
from app.modules.ai import engine_builder as B
from app.modules.ai import prompts as P
from app.modules.ai import provider as PR
from app.modules.ai.engine_themes import contrast
from app.modules.ai.kit import all_fields
from app.modules.forms.schema import form_schema_v1


class FakeMessages:
    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response, self.error, self.calls = response, error, []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def reply(data: Any, stop: str = "end_turn", iterations: list[Any] | None = None) -> Any:
    usage = SimpleNamespace(input_tokens=100, output_tokens=50, cache_read_input_tokens=900, cache_creation_input_tokens=0,
                            iterations=iterations)
    text = data if isinstance(data, str) else json.dumps(data)
    return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=text)], usage=usage,
                           model="claude-opus-5-5")


def provider(response: Any = None, error: Exception | None = None, model: str = "claude-opus-5-5") -> PR.AnthropicProvider:
    p = PR.AnthropicProvider("sk-test", model, "claude-haiku-5-5", 30, 0, True)
    fake = FakeMessages(response, error)
    p.client = SimpleNamespace(messages=fake, beta=SimpleNamespace(messages=fake))  # type: ignore[assignment]
    return p


def task(fast: bool = False) -> PR.ModelTask:
    return PR.ModelTask(task="labels", system="Stable rules", content='{"x": 1}', schema=P.LABELS,
                        standin=lambda: {"standin": True}, fast=fast)


async def test_the_request_sent_to_claude() -> None:
    p = provider(reply({"labels": []}))
    out = await p.complete(task())
    call = p.client.messages.calls[0]  # type: ignore[attr-defined]
    assert call["model"] == "claude-opus-5-5" and call["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert call["output_config"] == {"effort": "medium", "format": {"type": "json_schema", "schema": P.LABELS}}
    assert call["fallbacks"] == "default" and call["betas"] == ["server-side-fallback-2026-07-01"]
    assert "thinking" not in call and "tool_choice" not in call
    assert out.data == {"labels": []} and out.engine == "model"
    assert (out.usage.model_calls, out.usage.input_tokens, out.usage.cache_read_tokens) == (1, 100, 900)

    fast = provider(reply({"labels": []}))
    await fast.complete(task(fast=True))
    call = fast.client.messages.calls[0]  # type: ignore[attr-defined]
    assert call["model"] == "claude-haiku-5-5" and call["output_config"]["effort"] == "low" and "fallbacks" not in call


async def test_tokens_of_every_fallback_attempt_are_counted() -> None:
    parts = [SimpleNamespace(input_tokens=10, output_tokens=0, cache_read_input_tokens=0, cache_creation_input_tokens=5),
             SimpleNamespace(input_tokens=20, output_tokens=7, cache_read_input_tokens=3, cache_creation_input_tokens=0)]
    out = await provider(reply({"labels": []}, iterations=parts)).complete(task())
    assert (out.usage.input_tokens, out.usage.output_tokens, out.usage.cache_read_tokens, out.usage.cache_write_tokens) == (30, 7, 3, 5)


def _status(cls: type, code: int) -> Exception:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("nope", response=httpx2.Response(code, request=request), body=None)


@pytest.mark.parametrize(("error", "reason"), [
    (lambda: _status(anthropic.AuthenticationError, 401), "credentials"),
    (lambda: _status(anthropic.PermissionDeniedError, 403), "permission"),
    (lambda: _status(anthropic.RateLimitError, 429), "rate_limited"),
    (lambda: _status(anthropic.BadRequestError, 400), "bad_request"),
    (lambda: _status(anthropic.InternalServerError, 500), "status_500"),
    (lambda: anthropic.APITimeoutError(request=httpx2.Request("POST", "https://api.anthropic.com")), "timeout"),
    (lambda: anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com")), "unreachable"),
])
async def test_failures_become_short_reasons(error: Any, reason: str) -> None:
    with pytest.raises(PR.ProviderError) as caught:
        await provider(error=error()).complete(task())
    assert caught.value.reason == reason


@pytest.mark.parametrize(("response", "reason"), [
    (reply({}, stop="refusal"), "refused"), (reply({}, stop="max_tokens"), "cut_off"), (reply("not json {"), "not_json"),
    (SimpleNamespace(stop_reason="end_turn", content=[], usage=None, model="m"), "empty"),
])
async def test_answers_that_are_no_answer(response: Any, reason: str) -> None:
    with pytest.raises(PR.ProviderError) as caught:
        await provider(response).complete(task())
    assert caught.value.reason == reason


async def test_the_stand_in_answers_in_tests_and_without_a_key() -> None:
    assert isinstance(PR.get_provider(), PR.StandInProvider)
    assert get_settings().app_env == "test" or not get_settings().anthropic_api_key
    out = await PR.StandInProvider().complete(task())
    assert (out.data, out.engine, out.usage.model_calls) == ({"standin": True}, "standin", 0)


# ── Checks on what came back ──────────────────────────────────────────────────

SEED = {"type": "short_text", "label": "Q", "key": "", "required": False, "help": "", "placeholder": "",
        "options": [], "props": [], "rows": [], "formula": ""}


def seed(**over: Any) -> dict[str, Any]:
    return {**SEED, **over}


def draft(pages: list[Any], **over: Any) -> dict[str, Any]:
    return {"name": "A form", "description": "", "language": "fr", "source": "template", "based_on": "customer_feedback",
            "category": "business", "pages": pages, "rules": [], "thank_you": {"title": "", "message": ""}, "notes": [], **over}


def test_form_drafts_good_bad_and_broken() -> None:
    good = draft([{"title": "Page", "rows": [{"fields": [seed(label="Nom", key="nom"), seed(type="rating", label="Note",
                                                                                            props=[{"name": "max", "value": "50"}])]}]}])
    out = C.form_from_model(good, prompt="Formulaire", document=None, pages="auto")
    assert form_schema_v1.safe_parse(out["schema"])[0] and out["schema"]["settings"]["language"] == "fr"
    assert out["source"] == "template" and out["based_on"]["key"] == "customer_feedback"
    rating = all_fields(out["schema"])[1]
    assert rating["props"]["max"] == 5  # a rating out of 50 repaired
    # Too many questions on a row are split, a formula over unknown keys drops its field, pages put on one when asked
    crowded = draft([{"title": "A", "rows": [{"fields": [seed(label=f"Q{i}") for i in range(5)]}]},
                     {"title": "B", "rows": [{"fields": [seed(type="calculated", label="Total", formula="{nope} * 2")]}]}],
                    based_on="does_not_exist")
    out = C.form_from_model(crowded, prompt="x", document="Name:", pages="one")
    assert len(out["schema"]["pages"]) == 1 and all(len(r["fields"]) <= 2 for r in out["schema"]["pages"][0]["rows"])
    assert all(f["type"] != "calculated" for f in all_fields(out["schema"]))
    assert out["source"] == "document" and out["based_on"] is None
    for broken in ("text", [], {"pages": []}, draft([{"title": "x", "rows": [{"fields": [seed(type="section", label="Only a heading")]}]}])):
        with pytest.raises(C.OutputInvalid):
            C.form_from_model(broken, prompt="x", document=None, pages="auto")


def test_designs_good_bad_and_broken() -> None:
    data = {"suggestions": [
        {"key": "bold", "name": "Loud", "description": "Big.", "patch": [
            {"part": "colors.primary", "value": "#ffff00"}, {"part": "colors.input_border", "value": "red"},
            {"part": "header.band", "value": "color"}, {"part": "header.band_bg", "value": "#ffffaa"},
            {"part": "typography.font", "value": "comic"}, {"part": "buttons.full_width", "value": "true"}]},
        {"key": "nope", "name": "", "description": "", "patch": []}]}
    out = C.themes_from_model(data, colour="#ffff00", mood="", logo_url=None)
    assert [s["key"] for s in out][0] == "bold" and {s["key"] for s in out} == {"bold", "calm", "minimal"}
    assert contrast(out[0]["tokens"]["colors"]["primary"], "#ffffff") >= 4.5
    assert out[0]["tokens"]["typography"]["font"] != "comic"  # an unknown font: the stand-in's design for that key
    with pytest.raises(C.OutputInvalid):
        C.themes_from_model({"suggestions": []}, colour="#ffff00", mood="", logo_url=None)


SCHEMA = {"schema_version": 1, "pages": [{"id": "p1", "title": "One", "rows": [
    {"id": "r1", "fields": [{"id": "f1", "key": "allergies", "type": "toggle", "label": "Any allergies?"}]},
    {"id": "r2", "fields": [{"id": "f2", "key": "which", "type": "long_text", "label": "Which allergies?"}]},
    {"id": "r3", "fields": [{"id": "f3", "key": "mail", "type": "short_text", "label": "Your email"}]}]}]}


def assist(**lists: Any) -> dict[str, Any]:
    return {"add_fields": [], "set_help": [], "add_rules": [], "fixes": [], **lists}


def test_builder_help_good_bad_and_broken() -> None:
    def standin(action: str) -> Any:
        return lambda: B.assist_form(action, copy.deepcopy(SCHEMA), "Form")
    out = C.assist_from_model(assist(add_fields=[{"field": seed(type="phone", label="Phone number"), "page_id": "zzz", "after_id": ""},
                                                 {"field": seed(label="Which allergies"), "page_id": "", "after_id": ""}],
                                     set_help=[{"field_id": "f1", "help": "x"}]),
                              action="fields", schema=SCHEMA, standin=standin("fields"))
    assert [s["field"]["type"] for s in out] == ["phone"] and out[0]["page_id"] == "p1" and out[0]["after_id"] == "f3"
    rule = {"match": "all", "when": [{"field_id": "f1", "op": "true", "values": []}], "then": [{"action": "show", "target_id": "f2"}]}
    bad_rule = {"match": "all", "when": [{"field_id": "f1", "op": "gt", "values": ["3"]}], "then": [{"action": "show", "target_id": "f2"}]}
    out = C.assist_from_model(assist(add_rules=[rule, bad_rule]),
                              action="logic", schema=SCHEMA, standin=standin("logic"))
    assert len(out) == 1 and out[0]["rule"]["when"] == {"all": [{"field": "f1", "op": "true", "value": None}]}
    assert out[0]["note"]["code"] == "follow_up"
    out = C.assist_from_model(assist(fixes=[{"problem": "long_page", "field_id": "", "page_id": "p1", "text": "", "remove": False},
                                            {"problem": "duplicate", "field_id": "ghost", "page_id": "", "text": "", "remove": True}]),
                              action="check", schema=SCHEMA, standin=standin("check"))
    assert {(s["field_id"], s["problem"]) for s in out} >= {("f3", "email_type"), (None, "long_page")}
    with pytest.raises(C.OutputInvalid):
        C.assist_from_model({"nothing": 1}, action="help", schema=SCHEMA, standin=standin("help"))


def test_translations_rewrites_labels_plans_and_summaries() -> None:
    wanted = {"a": {"text": "<p>Hello <b>you</b></p>", "kind": "html"}, "b": {"text": "Name", "kind": "text"}}
    out = C.translations_from_model({"items": [{"key": "a", "translation": "<p>Bonjour <b>toi</b></p>"},
                                               {"key": "b", "translation": "<script>x</script>"}, {"key": "zzz", "translation": "Hm"}]}, wanted)
    assert out == {"a": "<p>Bonjour <b>toi</b></p>"}
    assert C.translations_from_model({"items": [{"key": "a", "translation": "<p>Bonjour toi</p>"}]}, wanted) == {}
    out = C.rewrites_from_model({"items": [{"key": "b", "rewrite": "Your name", "reasons": ["bogus"]},
                                           {"key": "b", "rewrite": "Again", "reasons": []}, {"key": "x", "rewrite": "No", "reasons": []}]},
                                {"b": "Name"})
    assert out == [{"key": "b", "text": "Name", "rewrite": "Your name", "reasons": ["plain_words"]}]
    labels = C.labels_from_model({"labels": [{"i": 0, "sentiment": "positive", "themes": ["staff", "x"]},
                                             {"i": 9, "sentiment": "positive", "themes": []}, {"i": 1, "sentiment": "meh", "themes": []}]}, 2)
    assert labels == {0: ("positive", ["staff"])}
    from datetime import date

    fields = [{"key": "office", "type": "radio", "label": "Office", "options": [{"value": "a", "label": "A"}]},
              {"key": "score", "type": "rating", "label": "Score"}]
    plan = C.plan_from_model({"kind": "average", "field_key": "office", "period": {"from": "2026-01-01", "to": "2030-01-01", "label": "x"},
                              "status": "any", "answer": {"field_key": "office", "value": "a"}, "bucket": "day"}, fields, date(2026, 10, 12))
    assert plan["field_key"] is None and plan["status"] is None and plan["answer"] == {"field_key": "office", "value": "a"}
    from app.modules.ai.engine_analysis import day_ms

    assert (plan["period"]["from"], plan["period"]["to"]) == (day_ms("2026-01-01"), day_ms("2026-10-12"))  # up to today
    with pytest.raises(C.OutputInvalid):
        C.plan_from_model({"kind": "guess"}, fields, date(2026, 10, 12))
    summary = C.summary_from_model({"points": [{"field_key": "office", "value": "Something else"},
                                               {"field_key": "ghost", "value": "x"}], "sentiment": "none", "themes": ["price", "x"]},
                                   fields, {"office": "a"}, lambda t: t)
    assert summary == {"points": [{"label": "Office", "value": "A"}], "sentiment": None, "themes": ["price"]}
    with pytest.raises(C.OutputInvalid):
        C.summary_from_model({"points": []}, fields, {}, lambda t: t)
