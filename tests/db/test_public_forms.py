"""Public forms (B7) end to end: the published form on the workspace host and on the shared forms host, the spam
check, submissions checked with the form's rules, one response per session / browser / identity, files, save and
resume, email verification, locked forms (password, invitation, member pass), short links, the server-rendered
page's internal read, and another workspace's host serving none of it."""

from __future__ import annotations

import uuid

import pytest

from app.core.config import get_settings
from app.modules.emails.service import SENT
from app.modules.public import router as public_router
from app.modules.public.pow import solve_work
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_builder import with_field
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def publish(owner: SecureClient, name: str, build) -> dict:  # noqa: ANN001
    """A published form whose draft `build(schema)` makes."""
    _, reply = await owner.request("POST", "/forms", body={"name": name})
    form = reply["data"]
    _, builder = await owner.request("GET", f"/forms/{form['id']}/builder")
    schema = build(builder["data"]["schema"])
    _, reply = await owner.request("PUT", f"/forms/{form['id']}/draft", body={"row_version": 1, "schema": schema})
    assert reply["success"], reply
    status, reply = await owner.request("POST", f"/forms/{form['id']}/publish", body={"row_version": 2})
    assert status == 200, reply
    return form


async def solved(client: SecureClient, key: str) -> dict:
    _, reply = await client.request("POST", f"/public/forms/{key}/challenge", body={})
    challenge = reply["data"]
    return {"token": challenge["token"], "nonce": solve_work(challenge["salt"], challenge["difficulty"])}


def session() -> dict[str, str]:
    return {"formalie-key": f"fill-{uuid.uuid4()}"}


async def test_public_forms_from_start_to_finish(app, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(public_router, "MIN_FILL_MS", 0)
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)

        def contact(schema: dict) -> dict:
            out = with_field(schema, "full_name", "Full name", required=True)
            out = with_field(out, "email", "Email", type="email", required=True)
            out = with_field(out, "qty", "How many", type="number", validation={"min": 1, "max": 5})
            out = with_field(out, "total", "Total", type="calculated", props={"formula": "{qty} * 10"})
            out = with_field(out, "attachment", "Attachment", type="file_upload", props={"accept": ".pdf", "max_files": 1})
            out["settings"] = {**out["settings"], "save_resume": True, "identity": {"email": "email", "verify": False}}
            return out
        form = await publish(owner, "Contact", contact)
        key = form["public_key"]

        # The page: open, the published questions, the theme resolved, legal links, no lock
        visitor = SecureClient(http)
        status, reply = await visitor.request("GET", f"/public/forms/{key}")
        assert status == 200, reply
        page = reply["data"]
        assert page["state"] == "open" and page["locked"] is False and page["lock"] is None
        assert [f["key"] for p in page["schema"]["pages"] for r in p["rows"] for f in r["fields"]] == [
            "full_name", "email", "qty", "total", "attachment"]
        assert page["schema"]["theme"]["colors"] and page["legal"]["terms_url"].startswith("https://")
        assert page["embed_ancestors"] == "*" and page["languages"] == ["en"] and page["seo"]["title"] == "Contact"

        # Spam check: no challenge, a reused one, a filled trap
        answers = {"full_name": "Ana Silva", "email": "ana@example.org", "qty": 2, "total": 999}
        _, reply = await visitor.request("POST", f"/public/forms/{key}/submit", body={"data": answers}, headers=session())
        assert reply["error"]["code"] == "FRM-RESP-1009"
        status, reply = await visitor.request("POST", f"/public/forms/{key}/submit",
                                              body={"data": answers, "trap": "bot"}, headers=session())
        assert status == 201 and reply["data"]["duplicate"] is False
        _, reply = await visitor.request("POST", f"/public/forms/{key}/submit", body={"data": {"qty": 9},
                                         "challenge": await solved(visitor, key)}, headers=session())
        assert reply["error"]["code"] == "FRM-RESP-1001"
        assert {d["field"]: d["message"] for d in reply["error"]["details"]} == {
            "full_name": "required", "email": "required", "qty": "max"}
        _, reply = await visitor.request("POST", f"/public/forms/{key}/submit", body={"data": answers}, headers=session())
        assert reply["error"]["code"] == "FRM-RESP-1009"

        # Stored once; the same session again gives the same response
        fill = session()
        proof = await solved(visitor, key)
        status, reply = await visitor.request("POST", f"/public/forms/{key}/submit",
                                              body={"data": answers, "challenge": proof}, headers=fill)
        assert status == 201, reply
        first = reply["data"]
        assert first["duplicate"] is False and first["thank_you"]["title"]
        _, reply = await visitor.request("POST", f"/public/forms/{key}/submit",
                                         body={"data": answers, "challenge": proof}, headers=fill)
        assert reply["data"] == {**first, "duplicate": True}
        _, reply = await visitor.request("POST", f"/public/forms/{key}/submit",
                                         body={"data": answers, "challenge": proof}, headers=session())
        assert reply["error"]["code"] == "FRM-RESP-1009"  # one solved challenge, one submission

        # Telling people apart: the same email → refused; a typo away → asked, then flagged
        _, reply = await visitor.request("POST", f"/public/forms/{key}/submit", body={
            "data": {**answers, "email": "ANA@example.org"}, "challenge": await solved(visitor, key)}, headers=session())
        assert reply["error"]["code"] == "FRM-RESP-1006"
        assert reply["error"]["details"][0]["field"] == "email" and "an•••@example.org" in reply["error"]["details"][0]["message"]
        near = {**answers, "email": "ana@exampel.org"}
        _, reply = await visitor.request("POST", f"/public/forms/{key}/submit", body={
            "data": near, "challenge": await solved(visitor, key)}, headers=session())
        assert reply["error"]["code"] == "FRM-RESP-1007"
        status, reply = await visitor.request("POST", f"/public/forms/{key}/submit", body={
            "data": near, "challenge": await solved(visitor, key), "confirmed_different": True}, headers=session())
        assert status == 201, reply

        # Files: a pre-signed link, the bytes, complete, then the answer
        _, reply = await visitor.request("POST", f"/public/forms/{key}/uploads", body={
            "field": "attachment", "file_name": "notes.txt", "content_type": "text/plain", "size": 5})
        assert reply["error"]["details"] == [{"field": "content_type", "message": "This file type is not allowed."}]
        pdf = b"%PDF-1.4 test"
        status, reply = await visitor.request("POST", f"/public/forms/{key}/uploads", body={
            "field": "attachment", "file_name": "cv.pdf", "content_type": "application/pdf", "size": len(pdf)})
        assert status == 201, reply
        ticket = reply["data"]
        stored = await http.put(ticket["upload_url"], content=pdf, headers={"content-type": "application/pdf"})
        assert stored.status_code == 204, stored.text
        _, reply = await visitor.request("POST", f"/public/forms/{key}/uploads/{ticket['upload_id']}/complete", body={})
        file_answer = reply["data"]
        assert file_answer["name"] == "cv.pdf" and file_answer["size"] == len(pdf)
        assert (await http.get(f"/api/v1/files/{file_answer['id']}")).status_code == 404  # personal data, not public
        with_file = {"full_name": "Ben Okoro", "email": "ben@example.org", "qty": 1, "attachment": [file_answer]}
        status, reply = await visitor.request("POST", f"/public/forms/{key}/submit", body={
            "data": with_file, "challenge": await solved(visitor, key)}, headers=session())
        assert status == 201, reply
        _, reply = await visitor.request("POST", f"/public/forms/{key}/submit", body={
            "data": {**with_file, "full_name": "Cara", "email": "cara@example.org"},
            "challenge": await solved(visitor, key)}, headers=session())
        assert reply["error"]["details"] == [{"field": "attachment", "message": "file"}]  # used by another response

        # Save and resume
        status, reply = await visitor.request("POST", f"/public/forms/{key}/sessions", body={
            "data": {"full_name": "Dee"}, "page": 0, "email": "dee@example.org"})
        assert status == 201 and reply["data"]["sent_to"] == "de•••@example.org"
        resume = reply["data"]["resume_token"]
        assert any("resume=" in m["text"] for m in SENT if m["to"] == "dee@example.org")
        await visitor.request("PUT", f"/public/forms/{key}/sessions/{resume}", body={"data": {"full_name": "Dee Dee"}, "page": 0})
        _, reply = await visitor.request("GET", f"/public/forms/{key}/sessions/{resume}")
        assert reply["data"]["data"] == {"full_name": "Dee Dee"}
        status, reply = await visitor.request("POST", f"/public/forms/{key}/submit", body={
            "data": {"full_name": "Dee Dee", "email": "dee@example.org"}, "resume_token": resume,
            "challenge": await solved(visitor, key)}, headers=session())
        assert status == 201, reply
        _, reply = await visitor.request("GET", f"/public/forms/{key}/sessions/{resume}")
        assert reply["error"]["code"] == "FRM-RESP-1003"

        # The form counts its responses; the audit trail has them as the Respondent
        _, reply = await owner.request("GET", f"/forms/{form['id']}")
        assert reply["data"]["responses_count"] == 4
        _, trail = await owner.request("GET", "/audit-logs", query={"filter[action]": "responses.submitted"})
        assert len(trail["data"]) == 4 and trail["data"][0]["actor"]["name"] == "Respondent"

        # One per browser when the form has no respondent email
        def survey(schema: dict) -> dict:
            out = with_field(schema, "rating", "Rating", type="rating")
            out["settings"] = {**out["settings"], "identity": {"email": None, "verify": False}}
            return out
        poll = await publish(owner, "Poll", survey)
        pkey = poll["public_key"]
        voter = SecureClient(http)
        status, _ = await voter.request("POST", f"/public/forms/{pkey}/submit", body={
            "data": {"rating": 4}, "challenge": await solved(voter, pkey)}, headers=session())
        assert status == 201
        _, reply = await voter.request("POST", f"/public/forms/{pkey}/submit", body={
            "data": {"rating": 3}, "challenge": await solved(voter, pkey)}, headers=session())
        assert reply["error"]["code"] == "FRM-RESP-1004"
        _, reply = await voter.request("POST", f"/public/forms/{pkey}/submit", body={
            "data": {"rating": 4}, "challenge": await solved(voter, pkey), "for_someone_else": True}, headers=session())
        assert reply["error"]["code"] == "FRM-RESP-1005"

        # Email verification
        def verified(schema: dict) -> dict:
            out = with_field(schema, "email", "Email", type="email", required=True)
            out["settings"] = {**out["settings"], "identity": {"email": "email", "verify": True}}
            return out
        checked = await publish(owner, "Checked", verified)
        ckey = checked["public_key"]
        _, reply = await visitor.request("POST", f"/public/forms/{ckey}/submit", body={
            "data": {"email": "eve@example.org"}, "challenge": await solved(visitor, ckey)}, headers=session())
        assert reply["error"]["code"] == "FRM-RESP-1008"
        _, reply = await visitor.request("POST", f"/public/forms/{ckey}/verify", body={"email": "Eve@Example.org"})
        assert "dev_code" not in reply["meta"]  # APP_ENV=development only (security review M5)
        code = next(m["values"]["code"] for m in reversed(SENT) if m["to"].lower() == "eve@example.org")
        assert reply["data"]["sent_to"] == "ev•••@example.org"
        _, reply = await visitor.request("POST", f"/public/forms/{ckey}/verify/confirm", body={"email": "eve@example.org", "code": "000000"})
        assert reply["error"]["code"] == "FRM-AUTH-1003"
        _, reply = await visitor.request("POST", f"/public/forms/{ckey}/verify/confirm", body={"email": "eve@example.org", "code": code})
        token = reply["data"]["token"]
        status, reply = await visitor.request("POST", f"/public/forms/{ckey}/submit", body={
            "data": {"email": "eve@example.org"}, "verification_token": token, "challenge": await solved(visitor, ckey)},
            headers=session())
        assert status == 201, reply

        # A password form: locked until the right password, for this browser only
        await owner.request("PUT", f"/forms/{poll['id']}/share", body={"access": "password", "password": "open-sesame-1"})
        stranger = SecureClient(http)
        _, reply = await stranger.request("GET", f"/public/forms/{pkey}")
        assert reply["data"]["locked"] is True and reply["data"]["lock"] == "password" and reply["data"]["schema"] is None
        _, reply = await stranger.request("POST", f"/public/forms/{pkey}/challenge", body={})
        assert reply["error"]["code"] == "FRM-FORM-1005"
        _, reply = await stranger.request("POST", f"/public/forms/{pkey}/unlock", body={"password": "wrong-one"})
        assert reply["error"]["code"] == "FRM-FORM-1017"
        _, reply = await stranger.request("POST", f"/public/forms/{pkey}/unlock", body={"password": "open-sesame-1"})
        assert reply["data"] == {"unlocked": True}
        _, reply = await stranger.request("GET", f"/public/forms/{pkey}")
        assert reply["data"]["locked"] is False and reply["data"]["schema"] is not None

        # Short link: on the shared forms host, it leads to the form's current link and counts the visit
        _, reply = await owner.request("POST", f"/forms/{form['id']}/short-link", body={})
        code = reply["data"]["short_link"]["code"]

        # Closed: no more responses
        await owner.request("POST", f"/forms/{checked['id']}/close", body={})
        _, reply = await visitor.request("GET", f"/public/forms/{ckey}")
        assert reply["data"]["state"] == "closed" and reply["data"]["schema"] is None

    async with client_for(app, host="forms.formalie.dev") as shared:
        anyone = SecureClient(shared)
        _, reply = await anyone.request("GET", f"/public/forms/{key}")
        assert reply["data"]["state"] == "open" and reply["data"]["workspace"]["subdomain"] == sub
        _, reply = await anyone.request("GET", f"/public/short/{code}")
        assert reply["data"]["target"].startswith(f"https://{sub}.formalie.dev") and reply["data"]["target"].endswith(f"/{key}/fill")
        _, reply = await anyone.request("GET", "/public/short/zzzzz")
        assert reply["error"]["code"] == "FRM-FORM-1001"

        # The server-rendered page's read: only with the server-only token
        bare = await shared.get(f"/api/v1/internal/public-forms/{key}")
        assert bare.status_code == 403
        monkeypatch.setattr(get_settings(), "internal_token", type(get_settings().fernet_keys[0])("server-only"))
        read = await shared.get(f"/api/v1/internal/public-forms/{key}", headers={"x-formalie-internal": "server-only"})
        assert read.status_code == 200 and read.json()["name"] == "Contact"
        missing = await shared.get("/api/v1/internal/public-forms/AbCdEfGhJk", headers={"x-formalie-internal": "server-only"})
        assert missing.status_code == 404 and missing.json() == {"error": {"code": "FRM-FORM-1001"}}
        short = await shared.get(f"/api/v1/internal/short/{code}", headers={"x-formalie-internal": "server-only"})
        assert short.json()["target"].endswith(f"/{key}/fill")
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, reply = await owner.request("GET", f"/forms/{form['id']}/share")
        assert reply["data"]["short_link"]["clicks"] == 2

    # Another workspace's host serves none of this workspace's forms
    other, _ = await new_workspace(app)
    async with client_for(app, host=f"{other}.formalie.dev") as http:
        _, reply = await SecureClient(http).request("GET", f"/public/forms/{key}")
        assert reply["error"]["code"] == "FRM-FORM-1001"
