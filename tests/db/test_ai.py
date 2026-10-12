"""The AI assistant (B13) end to end with the built-in stand-in (no key in tests, no internet): settings, usage,
history, every create / assist / write / analyse route with the mock's shapes key by key, apply and discard, the
allowance and the switches (FRM-AI-1001 to 1004), audit, a member's reach, another workspace seeing none of it,
expiry, and a fake model whose good, bad and broken answers are checked, repaired or replaced by the stand-in."""

from __future__ import annotations

from typing import Any

import pytest

from app.modules.ai import provider as PR
from app.modules.ai import tasks as AI_TASKS
from app.modules.design.theme import theme_schema
from app.modules.forms.schema import form_schema_v1
from app.modules.public import router as public_router
from tests.conftest import client_for
from tests.db.test_auth_flows import app, audit_actions, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_builder import with_field
from tests.db.test_destinations import submit
from tests.db.test_forms import member_of
from tests.db.test_public_forms import publish
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db

SETTINGS = {"enabled", "sources", "mask_personal", "keep_days", "monthly_credits", "updated_at", "updated_by", "brand_color"}
USAGE = {"period", "used", "limit", "previous", "requests", "people", "daily", "by_kind"}
ROW = {"id", "kind", "status", "title", "title_key", "by", "target", "credits", "created_at", "applied_at", "mine"}
DETAIL = ROW | {"prompt", "result", "read", "masked", "expires_at"}
INSIGHTS = {"total", "previous", "daily", "by_status", "by_kind", "people", "credits"}
FORM_DRAFT = {"request_id", "name", "description", "schema", "notes", "based_on", "source", "stats", "credits"}
ANALYSIS = {"request_id", "form", "period", "previous", "totals", "daily", "sentiment", "previous_sentiment", "themes",
            "ratings", "choices", "findings", "credits"}
ANSWER = {"request_id", "question", "kind", "value", "field", "rows", "filters", "period", "notes", "credits"}


def survey(schema: dict) -> dict:
    out = with_field(schema, "full_name", "Full name", type="full_name")
    out = with_field(out, "email", "Email", type="email")
    out = with_field(out, "office", "Which office did you visit?", type="radio",
                     options=[{"value": "riverside", "label": "Riverside"}, {"value": "harbour", "label": "Harbour"}])
    out = with_field(out, "rating", "Overall rating", type="rating", props={"max": 5})
    return with_field(out, "comments", "Comments", type="long_text")


def valid_form(schema: dict) -> None:
    ok, problems = form_schema_v1.safe_parse(schema)
    assert ok, problems


async def test_assistant_from_start_to_finish(app, superuser, monkeypatch) -> None:  # noqa: ANN001, F811
    monkeypatch.setattr(public_router, "MIN_FILL_MS", 0)
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)

        # Settings and an empty month
        _, reply = await owner.request("GET", "/ai/settings")
        assert set(reply["data"]) == SETTINGS and reply["data"]["enabled"] and reply["data"]["keep_days"] == 90
        assert reply["data"]["sources"] == {"forms": True, "responses": True, "data": False}
        _, reply = await owner.request("GET", "/ai/usage")
        usage = reply["data"]
        assert set(usage) == USAGE and usage["used"] == 0 and usage["limit"] == 100 and len(usage["daily"]) == 30
        assert set(usage["by_kind"]) == {"form", "template", "theme", "builder", "analysis", "question", "summary",
                                         "translate", "rewrite"}

        # A form from a description: proposed, then created
        status, reply = await owner.request("POST", "/ai/forms/draft", body={
            "prompt": "A sign-in form for visitors at reception: name, company, who they are visiting, arrival time, "
                      "a photo, phone +44 7700 900123 and agreement to the site rules."})
        assert status == 200, reply
        draft = reply["data"]
        assert set(draft) == FORM_DRAFT and draft["source"] == "list" and draft["credits"] == 5
        assert draft["name"] == "Visitor sign-in form" and set(draft["stats"]) == {"pages", "fields", "logic", "calculations"}
        valid_form(draft["schema"])
        assert set(draft["schema"]["theme"]) >= {"colors", "page", "buttons"}
        _, reply = await owner.request("GET", "/ai/requests")
        assert [set(r) for r in reply["data"]] == [ROW] and reply["data"][0]["status"] == "proposed"
        assert reply["data"][0]["mine"] is True and reply["meta"]["total"] == 1
        _, reply = await owner.request("GET", f"/ai/requests/{draft['request_id']}")
        detail = reply["data"]
        assert set(detail) == DETAIL | {"notes", "stats"} and "[number]" in detail["prompt"] and detail["masked"] is True
        status, reply = await owner.request("POST", f"/ai/requests/{draft['request_id']}/apply", body={"name": "Visitors"})
        assert status == 201 and set(reply["data"]["target"]) == {"type", "id", "name"}, reply
        form = reply["data"]["target"]
        _, reply = await owner.request("GET", f"/forms/{form['id']}")
        assert reply["data"]["name"] == "Visitors"
        status, reply = await owner.request("POST", f"/ai/requests/{draft['request_id']}/apply", body={"name": "Again"})
        assert (status, reply["error"]["code"]) == (409, "FRM-AI-1004")

        # Try again replaces a waiting draft; discard puts one aside
        _, reply = await owner.request("POST", "/ai/forms/draft", body={"prompt": "Customer feedback survey"})
        first = reply["data"]
        assert first["source"] == "template" and first["based_on"]["key"]
        _, reply = await owner.request("POST", "/ai/forms/draft", body={"prompt": "Customer feedback survey", "variant": 1,
                                                                         "replaces": first["request_id"], "pages": "one"})
        second = reply["data"]
        assert len(second["schema"]["pages"]) == 1
        _, reply = await owner.request("GET", f"/ai/requests/{first['request_id']}")
        assert reply["data"]["status"] == "discarded"
        _, reply = await owner.request("POST", f"/ai/requests/{second['request_id']}/discard")
        assert reply["data"] == {"discarded": True}
        status, reply = await owner.request("POST", f"/ai/requests/{second['request_id']}/discard")
        assert (status, reply["error"]["code"]) == (409, "FRM-AI-1004")

        # A template and a design
        _, reply = await owner.request("POST", "/ai/templates/draft", body={"prompt": "Equipment loan request for staff"})
        template = reply["data"]
        assert set(template) == FORM_DRAFT | {"category"} and template["credits"] == 5
        valid_form(template["schema"])
        status, reply = await owner.request("POST", f"/ai/requests/{template['request_id']}/apply", body={
            "name": "Equipment loans", "description": "Lend kit to staff", "category": template["category"]})
        assert status == 201 and reply["data"]["target"]["type"] == "template", reply
        _, reply = await owner.request("POST", "/ai/themes/draft", body={"colour": "#FACC15", "mood": "bold event"})
        designs = reply["data"]
        assert set(designs) == {"request_id", "colour", "suggestions", "sample", "credits"} and designs["colour"] == "#facc15"
        assert [s["key"] for s in designs["suggestions"]] == ["bold", "calm", "minimal"]
        for suggestion in designs["suggestions"]:
            assert set(suggestion) == {"key", "name", "description", "tokens"}
            assert theme_schema.safe_parse(suggestion["tokens"])[0]
        valid_form(designs["sample"])
        status, reply = await owner.request("POST", f"/ai/requests/{designs['request_id']}/apply", body={"name": "Bold", "key": "nope"})
        assert (status, reply["error"]["code"]) == (422, "FRM-GEN-1002")
        status, reply = await owner.request("POST", f"/ai/requests/{designs['request_id']}/apply", body={"name": "Bold", "key": "bold"})
        assert status == 201 and reply["data"]["target"]["type"] == "theme", reply

        # In the builder: every action, then the builder reports what it took
        _, reply = await owner.request("GET", f"/forms/{form['id']}/builder")
        schema = reply["data"]["schema"]
        for action in ("fields", "help", "logic", "check"):
            status, reply = await owner.request("POST", f"/ai/forms/{form['id']}/assist", body={"action": action, "schema": schema})
            assert status == 200 and set(reply["data"]) == {"request_id", "action", "suggestions", "credits"}, reply
            for suggestion in reply["data"]["suggestions"]:
                assert suggestion["kind"] in ("add_field", "set_help", "add_rule", "fix")
        assist = reply["data"]
        if assist["suggestions"]:
            status, reply = await owner.request("POST", f"/ai/requests/{assist['request_id']}/apply", body={"count": 1})
            assert status == 201 and reply["data"]["target"]["id"] == form["id"], reply

        # Translating and rewriting into the saved draft
        status, reply = await owner.request("POST", f"/ai/forms/{form['id']}/translate", body={"languages": ["fr", "en"]})
        assert status == 200, reply
        translation = reply["data"]
        assert set(translation) == {"request_id", "form", "from", "languages", "credits"} and translation["credits"] == 4
        language = translation["languages"][0]
        assert language["code"] == "fr" and set(language) == {"code", "items", "translated", "missing"}
        assert all(set(i) == {"key", "text", "kind", "page", "translation", "existing"} for i in language["items"])
        key = language["items"][0]["key"]
        status, reply = await owner.request("POST", f"/ai/requests/{translation['request_id']}/apply",
                                            body={"translations": {"fr": {key: "Texte"}}})
        assert status == 201, reply
        _, reply = await owner.request("GET", f"/forms/{form['id']}/builder")
        assert reply["data"]["schema"]["translations"]["fr"][key] == "Texte"
        assert "fr" in reply["data"]["schema"]["settings"]["languages"]
        status, reply = await owner.request("POST", f"/ai/forms/{form['id']}/translate", body={"languages": ["en"]})
        assert (status, reply["error"]["code"]) == (422, "FRM-GEN-1002")
        status, reply = await owner.request("POST", f"/ai/forms/{form['id']}/rewrite", body={"tone": "friendly"})
        rewrite = reply["data"]
        assert status == 200 and set(rewrite) == {"request_id", "form", "tone", "items", "reading", "total", "credits"}
        # A rewrite made before the form changed is refused (FRM-GEN-1009)
        _, reply = await owner.request("POST", f"/ai/forms/{form['id']}/translate", body={"languages": ["de"]})
        stale = reply["data"]
        _, reply = await owner.request("GET", f"/forms/{form['id']}")
        _, reply = await owner.request("PATCH", f"/forms/{form['id']}", body={"row_version": reply["data"]["row_version"],
                                                                              "name": "Visitors (renamed)"})
        assert reply["success"], reply
        status, reply = await owner.request("POST", f"/ai/requests/{stale['request_id']}/apply", body={"translations": {"de": {key: "Text"}}})
        assert (status, reply["error"]["code"]) == (409, "FRM-GEN-1009")

        # Analysing a form's responses
        published = await publish(owner, "Client survey", survey)
        for i, (office, rating, comment) in enumerate([("riverside", 5, "The staff were friendly and quick"),
                                                       ("harbour", 2, "Waiting time was too long and slow, email me at a@b.co"),
                                                       ("riverside", 4, "Price is fair")]):
            await submit(http, published["public_key"], {"full_name": f"Person {i}",
                                                         "office": office, "rating": rating, "comments": comment})
        status, reply = await owner.request("POST", "/ai/analysis", body={"form_id": published["id"]})
        assert status == 200 and set(reply["data"]) == ANALYSIS, reply
        analysis = reply["data"]
        assert analysis["totals"]["responses"] == 3 and analysis["totals"]["text_answers"] == 3
        assert analysis["sentiment"] == {"positive": 2, "neutral": 0, "negative": 1}
        assert all("@" not in example for theme in analysis["themes"] for example in theme["examples"])
        assert analysis["ratings"][0]["average"] == pytest.approx(3.7)
        status, reply = await owner.request("POST", "/ai/digest", body={"form_id": published["id"], "period": "month"})
        assert status == 200 and set(reply["data"]) == ANALYSIS and len(reply["data"]["daily"]) == 30
        status, reply = await owner.request("POST", "/ai/ask", body={"form_id": published["id"],
                                                                     "question": "Which office had the most visits?"})
        answer = reply["data"]
        assert status == 200 and set(answer) == ANSWER and answer["kind"] == "top", reply
        assert answer["rows"][0] == {"label": "Riverside", "count": 2, "share": 67}
        _, reply = await owner.request("GET", f"/forms/{published['id']}/responses")
        response_id = reply["data"][0]["id"]
        status, reply = await owner.request("POST", f"/ai/responses/{response_id}/summary")
        summary = reply["data"]
        assert status == 200 and set(summary) == {"request_id", "points", "sentiment", "themes", "credits"}, reply
        assert all(p["label"] not in ("Full name", "Email") for p in summary["points"])

        # The history, its cards and the month's usage
        _, reply = await owner.request("GET", "/ai/requests/insights")
        assert set(reply["data"]) == INSIGHTS and reply["data"]["total"] >= 15
        _, reply = await owner.request("GET", "/ai/requests", query={"filter[kind]": "analysis,question", "sort": "title"})
        assert {r["kind"] for r in reply["data"]} == {"analysis", "question"}
        _, reply = await owner.request("GET", "/ai/requests", query={"q": "client survey"})
        assert reply["data"] and all("Client survey" in (r["target"] or {}).get("name", "") or "Client survey" in r["title"]
                                     for r in reply["data"])
        _, reply = await owner.request("GET", "/ai/usage")
        used = reply["data"]["used"]
        assert used == sum(reply["data"]["by_kind"].values()) and reply["data"]["requests"] >= 15

        # Removing a request: gone from the history, still counted
        status, reply = await owner.request("DELETE", f"/ai/requests/{analysis['request_id']}")
        assert reply["data"] == {"deleted": True}
        status, reply = await owner.request("GET", f"/ai/requests/{analysis['request_id']}")
        assert (status, reply["error"]["code"]) == (404, "FRM-GEN-1004")
        _, reply = await owner.request("GET", "/ai/usage")
        assert reply["data"]["used"] == used

        # Switches: off, what it may read, the month's allowance
        _, reply = await owner.request("PATCH", "/ai/settings", body={"enabled": False})
        assert reply["data"]["enabled"] is False and reply["data"]["updated_by"]["name"]
        status, reply = await owner.request("POST", "/ai/forms/draft", body={"prompt": "Anything at all"})
        assert (status, reply["error"]["code"]) == (403, "FRM-AI-1001")
        _, reply = await owner.request("PATCH", "/ai/settings", body={"enabled": True, "sources": {"responses": False},
                                                                      "keep_days": 30})
        assert reply["data"]["sources"] == {"forms": True, "responses": False, "data": False}
        status, reply = await owner.request("POST", "/ai/analysis", body={"form_id": published["id"]})
        assert (status, reply["error"]["code"]) == (403, "FRM-AI-1003")
        superuser.execute("UPDATE formaly.ai_usage SET credits = 99 WHERE tenant_id = (SELECT id FROM platform.tenants "
                          "WHERE subdomain = %s)", (sub,))
        status, reply = await owner.request("POST", "/ai/forms/draft", body={"prompt": "Another form please"})
        assert (status, reply["error"]["code"]) == (429, "FRM-AI-1002")

    actions = audit_actions(superuser, email)
    for action in ("ai.applied", "ai.request_deleted", "ai.disabled", "ai.enabled", "forms.updated", "forms.created",
                   "forms.template_created", "forms.theme_created"):
        assert action in actions, action
    row = superuser.execute("SELECT engine, input_tokens FROM formaly.ai_requests WHERE kind = 'form' "
                            "AND tenant_id = (SELECT id FROM platform.tenants WHERE subdomain = %s) LIMIT 1", (sub,)).fetchone()
    assert row == ("standin", 0)


async def test_members_see_their_own_and_other_workspaces_nothing(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    other_sub, other_email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, reply = await owner.request("POST", "/ai/forms/draft", body={"prompt": "Volunteer sign-up form for our volunteers"})
        owners = reply["data"]["request_id"]
        published = await publish(owner, "Survey", survey)
        member, _ = await member_of(http, owner, sub)
        _, reply = await member.request("POST", "/ai/themes/draft", body={"colour": "#0f766e"})
        mine = reply["data"]["request_id"]
        _, reply = await member.request("GET", "/ai/requests")
        assert [r["id"] for r in reply["data"]] == [mine]
        status, reply = await member.request("GET", f"/ai/requests/{owners}")
        assert (status, reply["error"]["code"]) == (404, "FRM-GEN-1004")
        status, reply = await member.request("POST", f"/ai/requests/{owners}/apply", body={"name": "Mine"})
        assert (status, reply["error"]["code"]) == (404, "FRM-GEN-1004")
        status, reply = await member.request("PATCH", "/ai/settings", body={"enabled": False})
        assert (status, reply["error"]["code"]) == (403, "FRM-PERM-1001")
        _, reply = await owner.request("GET", "/ai/requests")
        assert {r["id"] for r in reply["data"]} == {owners, mine}

    async with client_for(app, host=f"{other_sub}.formalie.dev") as http:
        stranger = SecureClient(http)
        await sign_in(stranger, other_email, PASSWORD)
        _, reply = await stranger.request("GET", "/ai/requests")
        assert reply["data"] == []
        status, reply = await stranger.request("GET", f"/ai/requests/{owners}")
        assert (status, reply["error"]["code"]) == (404, "FRM-GEN-1004")
        status, reply = await stranger.request("DELETE", f"/ai/requests/{owners}")
        assert (status, reply["error"]["code"]) == (404, "FRM-GEN-1004")
        status, reply = await stranger.request("POST", f"/ai/requests/{owners}/discard")
        assert (status, reply["error"]["code"]) == (404, "FRM-GEN-1004")
        status, reply = await stranger.request("POST", "/ai/analysis", body={"form_id": published["id"]})
        assert (status, reply["error"]["code"]) == (404, "FRM-GEN-1004")
        status, reply = await stranger.request("POST", f"/ai/forms/{published['id']}/assist",
                                               body={"action": "help", "schema": {"schema_version": 1, "pages": [{"id": "p", "rows": []}]}})
        assert (status, reply["error"]["code"]) == (404, "FRM-GEN-1004")
        _, reply = await stranger.request("GET", "/ai/usage")
        assert reply["data"]["used"] == 0


async def test_expired_requests_are_emptied(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, reply = await owner.request("POST", "/ai/forms/draft", body={"prompt": "Incident report for staff"})
        old = reply["data"]["request_id"]
        _, reply = await owner.request("GET", "/ai/requests")
        assert len(reply["data"]) == 1
        superuser.execute("UPDATE formaly.ai_requests SET created_at = now() - interval '91 days' "
                          "WHERE tenant_id = (SELECT id FROM platform.tenants WHERE subdomain = %s)", (sub,))
        _, reply = await owner.request("GET", "/ai/requests")
        assert reply["data"] == []
        assert await AI_TASKS.expire_requests() >= 1
        row = superuser.execute("SELECT deleted_at IS NOT NULL, prompt, output IS NULL FROM formaly.ai_requests "
                                "WHERE tenant_id = (SELECT id FROM platform.tenants WHERE subdomain = %s)", (sub,)).fetchone()
        assert row == (True, "", True)
        status, _ = await owner.request("GET", f"/ai/requests/{old}")
        assert status == 404


class FakeModel:
    """A model that answers with what the test gives it, and counts tokens."""

    name = "fake"

    def __init__(self, answers: dict[str, Any]) -> None:
        self.answers, self.seen = answers, []

    async def complete(self, task: PR.ModelTask) -> PR.ModelReply:
        self.seen.append(task)
        answer = self.answers.get(task.task)
        if isinstance(answer, Exception):
            raise answer
        return PR.ModelReply(answer, "model", "claude-test", PR.Usage(1, 1200, 300, 800, 0))


def seed(**over: Any) -> dict[str, Any]:
    return {"type": "short_text", "label": "Q", "key": "", "required": False, "help": "", "placeholder": "",
            "options": [], "props": [], "rows": [], "formula": "", **over}


GOOD_FORM = {
    "name": "Event registration", "description": "Sign up for the event", "language": "en", "source": "list",
    "based_on": "", "category": "events",
    "pages": [{"title": "You", "rows": [
        {"fields": [seed(type="full_name", label="Your name", key="name", required=True)]},
        {"fields": [seed(type="toggle", label="Any allergies?", key="allergies"),
                    seed(type="long_text", label="Which allergies?", key="allergy details")]},
        {"fields": [seed(type="number", label="Tickets", key="tickets", required=True),
                    seed(type="currency", label="Price", key="price", required=True),
                    seed(type="calculated", label="Total", key="total", props=[{"name": "format", "value": "currency"}],
                         formula="{tickets} * {price}")]},
        {"fields": [seed(type="radio", label="Session"), seed(type="weird_type", label="Mystery", key="x")]},
    ]}],
    "rules": [{"match": "all", "when": [{"key": "allergies", "op": "true", "values": []}],
               "then": [{"action": "show", "target": "allergy details", "value": ""}]},
              {"match": "all", "when": [{"key": "nothing", "op": "eq", "values": ["x"]}],
               "then": [{"action": "show", "target": "tickets", "value": ""}]}],
    "thank_you": {"title": "Thanks", "message": "See you there."},
    "notes": [{"code": "follow_up", "params": [{"name": "field", "value": "Which allergies?"}]}, {"code": "bogus", "params": []}],
}


async def test_model_answers_are_checked_repaired_or_replaced(app, superuser, monkeypatch) -> None:  # noqa: ANN001, F811
    monkeypatch.setattr(public_router, "MIN_FILL_MS", 0)
    sub, email = await new_workspace(app)
    fake = FakeModel({"form_draft": GOOD_FORM, "theme_draft": {"suggestions": [
        {"key": "minimal", "name": "Quiet", "description": "Clean.", "patch": [{"part": "colors.primary", "value": "#fde047"}]},
        {"key": "minimal", "name": "Twice", "description": "", "patch": []}]},
        "labels": {"labels": [{"i": 0, "sentiment": "negative", "themes": ["price", "nonsense"]}]},
        "question": {"kind": "count", "field_key": "", "period": {"from": "", "to": "", "label": ""}, "status": "any",
                     "answer": {"field_key": "", "value": ""}, "bucket": "month"},
        "summary": "broken", "rewrite": PR.ProviderError("timeout")})
    PR.use_provider(fake)
    try:
        async with client_for(app, host=f"{sub}.formalie.dev") as http:
            owner = SecureClient(http)
            await sign_in(owner, email, PASSWORD)
            status, reply = await owner.request("POST", "/ai/forms/draft", body={"prompt": "Event registration with my email ana@example.com"})
            assert status == 200, reply
            draft = reply["data"]
            valid_form(draft["schema"])
            fields = {f["key"]: f for p in draft["schema"]["pages"] for r in p["rows"] for f in r["fields"]}
            assert fields["x"]["type"] == "short_text"  # unknown type repaired
            assert len(fields["session"]["options"]) == 3  # a choice without options gets some
            assert fields["total"]["props"]["formula"] == "{tickets} * {price}"
            assert [r["then"][0]["target"] for r in draft["schema"]["logic"]] == ["f_allergy_details"]  # the broken rule dropped
            assert draft["notes"] == [{"code": "follow_up", "params": {"field": "Which allergies?"}}]
            assert "ana@example.com" not in fake.seen[-1].content and "[email]" in fake.seen[-1].content

            # Designs: a light button colour is darkened, a missing design is the stand-in's
            _, reply = await owner.request("POST", "/ai/themes/draft", body={"colour": "#fde047"})
            designs = reply["data"]["suggestions"]
            assert [d["key"] for d in designs] == ["minimal", "calm", "bold"] and designs[0]["name"] == "Quiet"
            from app.modules.ai.engine_themes import contrast

            assert all(contrast(d["tokens"]["colors"]["primary"], "#ffffff") >= 4.5 for d in designs)

            # Broken output and a provider that times out: the stand-in answers, the request says why
            published = await publish(owner, "Survey", survey)
            await submit(http, published["public_key"], {"full_name": "A", "rating": 4, "comments": "Too expensive"})
            _, reply = await owner.request("POST", "/ai/analysis", body={"form_id": published["id"]})
            assert reply["data"]["themes"][0]["key"] == "price" and reply["data"]["sentiment"]["negative"] == 1
            _, reply = await owner.request("GET", f"/forms/{published['id']}/responses")
            status, reply = await owner.request("POST", f"/ai/responses/{reply['data'][0]['id']}/summary")
            assert status == 200 and reply["data"]["points"], reply
            status, reply = await owner.request("POST", f"/ai/forms/{published['id']}/rewrite", body={"tone": "plain"})
            assert status == 200, reply
            _, reply = await owner.request("POST", "/ai/ask", body={"form_id": published["id"], "question": "how many?"})
            assert reply["data"]["kind"] == "count" and reply["data"]["value"] == 1
    finally:
        PR.use_provider(None)
    rows = dict(superuser.execute(
        "SELECT kind || ':' || coalesce(title, ''), engine || ':' || coalesce(fallback_reason, '') FROM formaly.ai_requests "
        "WHERE tenant_id = (SELECT id FROM platform.tenants WHERE subdomain = %s)", (sub,)).fetchall())
    engines = {k.split(":")[0]: v for k, v in rows.items()}
    assert engines["form"] == "model:" and engines["rewrite"] == "fallback:timeout"
    assert engines["summary"].startswith("fallback:invalid")
    usage = superuser.execute("SELECT model_calls, input_tokens, cache_read_tokens FROM formaly.ai_usage "
                              "WHERE tenant_id = (SELECT id FROM platform.tenants WHERE subdomain = %s)", (sub,)).fetchone()
    assert usage[0] >= 5 and usage[1] >= 5 * 1200 and usage[2] >= 5 * 800
