"""Workspace settings and uploads (B3) end to end, each test on a new workspace made through the real sign-up:
sections, validation like zod, lock-out guards, the plan, pictures through uploads, files, sessions and activity."""

from __future__ import annotations

import re
import struct
import uuid
import zlib

import pytest

from tests.conftest import client_for
from tests.db.test_auth_flows import app, audit_actions, last_code, seeded, sign_in  # noqa: F401  (fixtures)
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def new_workspace(app) -> tuple[str, str]:  # noqa: ANN001
    """Sign-up on manage.* → (subdomain, the Owner's email); the Owner's password is PASSWORD below."""
    sub = f"set{uuid.uuid4().hex[:8]}"
    email = f"owner@{sub}.test"
    async with client_for(app, host="manage.formalie.dev") as http:
        manage = SecureClient(http)
        _, reply = await manage.request("POST", "/auth/signup", body={
            "first_name": "Olu", "last_name": "Ade", "email": email, "password": PASSWORD})
        challenge = reply["data"]["challenge_id"]
        await manage.request("POST", "/auth/otp/verify", body={"challenge_id": challenge, "code": last_code(email)})
        _, reply = await manage.request("POST", "/auth/signup/complete", body={
            "challenge_id": challenge, "company_name": "Settings Co", "subdomain": sub})
        assert reply["success"], reply
    return sub, email


PASSWORD = "Correct-Horse-9"


def png() -> bytes:
    """A real 1×1 PNG."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00")) + chunk(b"IEND", b""))


async def test_sections_validation_and_audit(app, superuser) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        status, reply = await owner.request("GET", "/settings")
        assert status == 200
        data = reply["data"]
        assert set(data) == {"company", "branding", "localisation", "signin", "security", "notifications", "emails",
                             "privacy", "form_defaults", "appearance", "updated"}
        assert data["company"]["display_name"] == "Settings Co" and data["updated"]["company"] is None
        assert data["notifications"]["events"]["security_alert"] == {"in_app": True, "email": True, "to": "admins",
                                                                      "people": []}

        company = {**data["company"], "display_name": "  Settings Company  ", "website": "https://settings.example",
                   "address": {**data["company"]["address"], "country": "GB", "city": " Leeds "}}
        status, reply = await owner.request("PATCH", "/settings/company", body=company)
        assert status == 200, reply
        assert reply["data"]["display_name"] == "Settings Company" and reply["data"]["address"]["city"] == "Leeds"
        _, again = await owner.request("GET", "/settings")
        assert again["data"]["updated"]["company"]["by"] == "Olu Ade"
        _, trail = await owner.request("GET", "/audit-logs", query={"filter[action]": "settings.updated"})
        fields = {c["field"]: c for c in trail["data"][0]["changes"]}
        assert fields["display_name"] == {"field": "display_name", "before": "Settings Co", "after": "Settings Company"}
        assert fields["address.country"]["after"] == "GB" and trail["data"][0]["resource"]["name"] == "Company"
        name = superuser.execute("SELECT o.name FROM formaly.organisations o JOIN platform.tenants t "
                                 "ON t.primary_organisation_id = o.id WHERE t.subdomain = %s", (sub,)).fetchone()
        assert name == ("Settings Company",)

        # The same problems, in the same words, as zod
        status, reply = await owner.request("PATCH", "/settings/company", body={**company, "display_name": "S",
                                                                                 "website": "nope", "industry": "space"})
        assert (status, reply["error"]["code"]) == (422, "FRM-GEN-1002")
        assert [(d["field"], d["message"]) for d in reply["error"]["details"]] == [
            ("display_name", "Too small: expected string to have >=2 characters"),
            ("industry", 'Invalid option: expected one of "professional_services"|"legal"|"finance"|"healthcare"|'
                         '"education"|"government"|"non_profit"|"technology"|"retail"|"manufacturing"|"hospitality"|'
                         '"real_estate"|"logistics"|"energy"|"media"|"other"'),
            ("website", "website")]

        # Lock-out guards and the plan
        signin = {**data["signin"], "allowed_domains": ["other.example"]}
        _, reply = await owner.request("PATCH", "/settings/signin", body=signin)
        assert reply["error"]["code"] == "FRM-AUTH-1017" and reply["error"]["details"][0]["message"] == "own_domain"
        _, reply = await owner.request("PATCH", "/settings/signin", body={**data["signin"], "methods": ["password", "google"]})
        assert reply["error"]["code"] == "FRM-PLAN-1002"  # Starter: no new social sign-in
        security = data["security"]
        _, reply = await owner.request("PATCH", "/settings/security", body={
            **security, "ip_allowlist": {"enabled": True, "entries": [{"value": "10.0.0.0/8", "label": None}]}})
        assert reply["error"]["code"] == "FRM-AUTH-1017" and reply["error"]["details"][0]["message"] == "own_ip"
        status, reply = await owner.request("PATCH", "/settings/security", body={
            **security, "ip_allowlist": {"enabled": True, "entries": [{"value": "203.0.113.0/24", "label": " Office "},
                                                                      {"value": "", "label": None}]}})
        assert status == 200 and reply["data"]["ip_allowlist"]["entries"] == [{"value": "203.0.113.0/24", "label": "Office"}]
        _, trail = await owner.request("GET", "/audit-logs", query={"filter[action]": "settings.updated"})
        # an empty list reads as "" (String([]) in JavaScript), as in the mock
        assert {"field": "ip_allowlist.entries", "before": "", "after": "203.0.113.0/24 (Office)"} in trail["data"][0]["changes"]

        _, reply = await owner.request("PATCH", "/settings/form_defaults", body={**data["form_defaults"], "theme_id": "t1"})
        assert reply["error"]["details"] == [{"field": "theme_id", "message": "theme"}]
        _, reply = await owner.request("GET", "/settings/nonsense")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        status, reply = await owner.request("PATCH", "/settings/appearance", body={**data["appearance"], "primary": "blue"})
        assert status == 200 and reply["data"]["primary"] == "blue"


async def test_members_read_only_what_the_portal_needs(app) -> None:  # noqa: ANN001
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        member = SecureClient(http)
        await sign_in(member, "staff@remedylegal.test")
        for path in ("/settings/localisation", "/settings/appearance", "/settings/form_defaults"):
            status, reply = await member.request("GET", path)
            assert status == 200, (path, reply)
        for method, path in (("GET", "/settings"), ("GET", "/settings/company"), ("GET", "/settings/security/sessions"),
                             ("PATCH", "/settings/localisation")):
            _, reply = await member.request(method, path, body={} if method == "PATCH" else None)
            assert reply["error"]["code"] == "FRM-PERM-1001", path
        _, reply = await member.request("POST", "/uploads", body={"purpose": "logo", "file_name": "a.png",
                                                                  "content_type": "image/png", "size": 10})
        assert reply["error"]["code"] == "FRM-PERM-1001"


async def test_logo_upload_branding_and_file(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    image = png()
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, reply = await owner.request("POST", "/uploads", body={"purpose": "logo", "file_name": "logo.png",
                                                                 "content_type": "image/svg+xml", "size": len(image)})
        assert reply["error"]["details"] == [{"field": "content_type", "message": "This file type is not allowed."}]
        _, reply = await owner.request("POST", "/uploads", body={"purpose": "logo", "file_name": "logo.png",
                                                                 "content_type": "image/png", "size": 3 * 1024 * 1024})
        assert reply["error"]["details"] == [{"field": "size", "message": "The file is larger than 2 MB."}]

        status, ticket = await owner.request("POST", "/uploads", body={"purpose": "logo", "file_name": "logo.png",
                                                                       "content_type": "image/png", "size": len(image)})
        assert status == 200, ticket
        ticket = ticket["data"]
        assert ticket["method"] == "PUT" and len(ticket["upload_id"]) == 27 and ticket["max_bytes"] == 2 * 1024 * 1024
        url = ticket["upload_url"]
        bad = await http.put(url, content=b"not a picture" + b"x" * (len(image) - 13), headers={"content-type": "image/png"})
        assert (bad.status_code, bad.json()) == (400, {"error": "The file is not a valid image."})
        status, ticket = await owner.request("POST", "/uploads", body={"purpose": "logo", "file_name": "logo.png",
                                                                       "content_type": "image/png", "size": len(image)})
        ticket = ticket["data"]
        assert (await http.put(ticket["upload_url"], content=image, headers={"content-type": "image/jpeg"})).status_code == 400
        assert (await http.put(ticket["upload_url"], content=image, headers={"content-type": "image/png"})).status_code == 204
        assert (await http.put(ticket["upload_url"], content=image, headers={"content-type": "image/png"})).status_code == 403

        status, done = await owner.request("POST", f"/uploads/{ticket['upload_id']}/complete")
        assert status == 200 and done["data"]["size"] == len(image)
        assert re.fullmatch(r"/api/v1/files/[A-Za-z0-9_-]{27}", done["data"]["url"])  # a reference, never the id

        _, settings = await owner.request("GET", "/settings/branding")
        status, reply = await owner.request("PATCH", "/settings/branding", body={
            "logo_upload_id": ticket["upload_id"], "brand_color": "#1a2b3c", "signin_message": None})
        assert status == 200, reply
        assert reply["data"]["logo_url"] == done["data"]["url"] and reply["data"]["brand_color"] == "#1A2B3C"
        _, reply = await owner.request("PATCH", "/settings/branding", body={
            "logo_upload_id": str(uuid.uuid4()), "brand_color": None, "signin_message": None})
        assert reply["error"]["details"] == [{"field": "logo", "message": "upload_again"}]
        _, trail = await owner.request("GET", "/audit-logs", query={"filter[action]": "settings.updated"})
        assert {"field": "logo_url", "before": None, "after": "uploaded"} in trail["data"][0]["changes"]

        _, profile = await owner.request("GET", "/tenants/public")
        assert profile["data"]["logo_url"] == done["data"]["url"]

    # The file, on any host (a public form shows it too); a typed-in id never works
    async with client_for(app, host="forms.formalie.dev") as anyone:
        served = await anyone.get(done["data"]["url"])
        assert served.status_code == 200 and served.content == image
        assert served.headers["content-type"] == "image/png" and served.headers["x-content-type-options"] == "nosniff"
        assert (await anyone.get(f"/api/v1/files/{uuid.uuid4()}")).status_code == 404


async def test_sessions_and_activity(app, superuser) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http, \
            client_for(app, host=f"{sub}.formalie.dev") as other_http:
        owner, elsewhere = SecureClient(http), SecureClient(other_http)
        await sign_in(owner, email, PASSWORD)
        await sign_in(elsewhere, email, PASSWORD)
        _, reply = await owner.request("POST", "/auth/login", body={"email": email, "password": "Wrong-Pass-1"})
        assert reply["error"]["code"] == "FRM-AUTH-1002"

        status, sessions = await owner.request("GET", "/settings/security/sessions")
        assert status == 200 and len(sessions["data"]) == 2
        assert [s["current"] for s in sessions["data"]].count(True) == 1
        assert sessions["data"][0]["user"] == {"name": "Olu Ade", "email": email} and len(sessions["data"][0]["id"]) == 27

        _, activity = await owner.request("GET", "/settings/security/activity")
        data = activity["data"]
        assert data["my_ip"] == "203.0.113.7" and len(data["days"]) == 14
        assert data["totals"]["succeeded"] == 2 and data["totals"]["failed"] == 1
        assert data["days"][-1]["succeeded"] == 2 and data["recent"][0]["action"] == "auth.login.failed"

        status, reply = await owner.request("POST", "/settings/security/sessions/sign-out", body={"everyone_else": True})
        assert status == 200 and reply["data"] == {"signed_out": 1}
        _, reply = await elsewhere.request("GET", "/me")
        assert reply["error"]["code"] == "FRM-AUTH-1011"
        status, _ = await owner.request("GET", "/me")
        assert status == 200  # never the caller's own
        assert "auth.session.revoked" in audit_actions(superuser, email)
