"""My profile (B4) on a new workspace: profile and photo, password, authenticator app with recovery codes (used at
sign-in), text-message phone, my sessions, tips on new pages."""

from __future__ import annotations

import base64
import re

import pyotp
import pytest

from app.modules.notifications.sms import SENT as SMS
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_settings import PASSWORD, new_workspace, png
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db

NEW = "Brand-New-Pass-5"


async def test_my_profile_from_start_to_finish(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http, \
            client_for(app, host=f"{sub}.formalie.dev") as other_http:
        me, elsewhere = SecureClient(http), SecureClient(other_http)
        await sign_in(me, email, PASSWORD)
        await sign_in(elsewhere, email, PASSWORD)

        status, reply = await me.request("GET", "/me/profile")
        assert status == 200 and reply["data"]["role"] == "owner" and reply["data"]["notifications"] == {
            "responses": True, "digest": False, "mentions": True, "product": False}
        assert reply["data"]["two_step"] == {"app": False, "recovery_left": 0, "phone": None, "sms_allowed": False}

        photo = "data:image/png;base64," + base64.b64encode(png()).decode()
        _, reply = await me.request("PATCH", "/me/profile", body={
            "first_name": " Olu ", "photo": photo, "time_zone": "Europe/London", "notifications": {"digest": True}})
        data = reply["data"]
        assert data["first_name"] == "Olu" and data["time_zone"] == "Europe/London" and data["notifications"]["digest"]
        assert re.fullmatch(r"/api/v1/files/[A-Za-z0-9_-]{27}", data["photo"])
        assert (await http.get(data["photo"])).content == png()
        _, reply = await me.request("PATCH", "/me/profile", body={"time_zone": "Mars/Base"})
        assert reply["error"]["code"] == "FRM-GEN-1002"

        # Password: the current one checked; other devices sign in again
        _, reply = await me.request("POST", "/me/password", body={"current": "wrong", "password": NEW})
        assert reply["error"]["code"] == "FRM-AUTH-1001" and reply["error"]["details"] == [{"field": "current", "message": "wrong"}]
        _, reply = await me.request("POST", "/me/password", body={"current": PASSWORD, "password": NEW})
        assert reply["data"] == {"changed": True}
        _, reply = await elsewhere.request("GET", "/me")
        assert reply["error"]["code"] == "FRM-AUTH-1011"
        status, _ = await me.request("GET", "/me")
        assert status == 200

        # Authenticator app, then a sign-in with a recovery code
        _, reply = await me.request("POST", "/me/two-step/app")
        secret = reply["data"]["secret"]
        assert reply["data"]["uri"].startswith("otpauth://totp/") and f"secret={secret}" in reply["data"]["uri"]
        _, reply = await me.request("POST", "/me/two-step/app/confirm", body={"code": "000000"})
        assert reply["error"]["code"] == "FRM-AUTH-1003"
        _, reply = await me.request("POST", "/me/two-step/app/confirm", body={"code": pyotp.TOTP(secret).now()})
        codes = reply["data"]["recovery_codes"]
        assert len(codes) == 10 and all(re.fullmatch(r"[0-9a-f]{4}-[0-9a-f]{4}", c) for c in codes)
        fresh = SecureClient(other_http)
        _, challenge = await fresh.request("POST", "/auth/login", body={"email": email, "password": NEW})
        assert challenge["data"]["channel"] == "totp"
        status, reply = await fresh.request("POST", "/auth/otp/verify", body={
            "challenge_id": challenge["data"]["challenge_id"], "code": codes[0]})
        assert status == 200, reply
        _, profile = await me.request("GET", "/me/profile")
        assert profile["data"]["two_step"]["app"] and profile["data"]["two_step"]["recovery_left"] == 9
        _, reply = await me.request("POST", "/me/two-step/recovery", body={"password": NEW})
        assert len(reply["data"]["recovery_codes"]) == 10
        _, reply = await me.request("POST", "/me/two-step/app/remove", body={"password": "nope"})
        assert reply["error"]["details"] == [{"field": "password", "message": "wrong"}]
        _, reply = await me.request("POST", "/me/two-step/app/remove", body={"password": NEW})
        assert reply["data"]["two_step"] == {"app": False, "recovery_left": 0, "phone": None, "sms_allowed": False}

        # Text messages: only when the workspace allows them
        _, reply = await me.request("POST", "/me/two-step/phone", body={"phone": "+44 7700 900123"})
        assert reply["error"]["details"] == [{"field": "phone", "message": "sms_off"}]
        _, signin = await me.request("GET", "/settings/signin")
        await me.request("PATCH", "/settings/signin", body={**signin["data"], "code": {**signin["data"]["code"], "sms": True}})
        _, reply = await me.request("POST", "/me/two-step/phone", body={"phone": "+44 7700 900123"})
        assert reply["data"] == {"masked": "+44 ••••••0123"}
        code = re.search(r"\d{6}", SMS[-1]["text"]).group(0)  # type: ignore[union-attr]
        _, reply = await me.request("POST", "/me/two-step/phone/confirm", body={"code": code})
        assert reply["data"]["two_step"]["phone"] == "+44 ••••••0123"
        _, reply = await me.request("DELETE", "/me/two-step/phone")
        assert reply["data"]["two_step"]["phone"] is None

        # My sessions
        _, sessions = await me.request("GET", "/me/sessions")
        assert len(sessions["data"]) == 2 and [s["current"] for s in sessions["data"]].count(True) == 1
        current = next(s["id"] for s in sessions["data"] if s["current"])
        other = next(s["id"] for s in sessions["data"] if not s["current"])
        _, reply = await me.request("DELETE", f"/me/sessions/{current}")
        assert reply["error"]["code"] == "FRM-USER-1005"
        _, reply = await me.request("DELETE", f"/me/sessions/{other}")
        assert [s["id"] for s in reply["data"]] == [current]
        _, reply = await me.request("POST", "/me/sessions/sign-out-others")
        assert len(reply["data"]) == 1

        # Tips on new pages
        _, reply = await me.request("GET", "/me/tours")
        assert reply["data"] == {"enabled": True, "seen": []}
        await me.request("PATCH", "/me/tours", body={"seen": "forms"})
        _, reply = await me.request("PATCH", "/me/tours", body={"seen": "forms", "enabled": False})
        assert reply["data"] == {"enabled": False, "seen": ["forms"]}
        _, reply = await me.request("PATCH", "/me/tours", body={"reset": True, "enabled": True})
        assert reply["data"] == {"enabled": True, "seen": []}

        _, trail = await me.request("GET", "/audit-logs", query={"page_size": 100})
        actions = {e["action"] for e in trail["data"]}
        assert {"users.profile_updated", "auth.password.changed", "auth.two_step.enabled", "auth.two_step.disabled",
                "auth.recovery_codes.created", "auth.session.revoked"} <= actions
