"""Security review fixes (B17, 2026-10-12) that need no database: code tries counted atomically and kept over
resends (M1), the authenticator app as the only offered channel (M2), security emails through Formalie's relay in
Formalie's wording (H3), what a support session may never do (H3, M4), APP_ENV failing safe (M5), single-line email
settings (L20)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.errors import FrmError
from app.core.startup import UnsafeStart, ensure_safe_start, startup_problems
from app.modules.auth import challenges
from app.modules.platform_bridge.support import support_refusal

TENANT = {"id": uuid.uuid4(), "organisation_id": uuid.uuid4(), "name": "Acme"}


async def _code_error(challenge_id: str, code: str) -> str:
    try:
        await challenges.verify_code(challenge_id, code, "login")
    except FrmError as error:
        return error.code
    return "ok"


# ── M1: tries counted before comparing, one total per challenge ────────────────────

async def test_parallel_wrong_guesses_each_count(redis) -> None:  # noqa: ANN001
    ch, code = await challenges.create_challenge(purpose="login", email="a@example.org", channel="email",
                                                 channels=["email"], tenant=TENANT)
    results = await asyncio.gather(*[_code_error(ch.id, "000000") for _ in range(12)])
    assert results.count("FRM-AUTH-1003") == 4 and results.count("FRM-AUTH-1004") == 8
    # Every try counted, so even the right code is refused now
    assert await _code_error(ch.id, code or "") == "FRM-AUTH-1004"


async def test_resend_keeps_the_tries_already_used(redis, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(challenges, "RESEND_AFTER_S", 0)
    ch, _ = await challenges.create_challenge(purpose="reset", email="a@example.org", channel="email",
                                              channels=["email"], tenant=TENANT)
    for _ in range(4):
        with pytest.raises(FrmError):
            await challenges.verify_code(ch.id, "000000", "reset")
    _, code = await challenges.resend(ch.id, None)
    with pytest.raises(FrmError) as wrong:
        await challenges.verify_code(ch.id, "000000", "reset")
    assert wrong.value.code == "FRM-AUTH-1004"  # the fifth try overall, not the first after the resend
    with pytest.raises(FrmError) as locked:
        await challenges.verify_code(ch.id, code or "", "reset")
    assert locked.value.code == "FRM-AUTH-1004"
    with pytest.raises(FrmError) as no_more:
        await challenges.resend(ch.id, None)
    assert no_more.value.code == "FRM-AUTH-1004"


async def test_one_right_code_wins_once(redis) -> None:  # noqa: ANN001
    ch, code = await challenges.create_challenge(purpose="login", email="a@example.org", channel="email",
                                                 channels=["email"], tenant=TENANT)
    results = await asyncio.gather(*[_code_error(ch.id, code or "") for _ in range(5)])
    assert results.count("ok") == 1 and results.count("FRM-AUTH-1003") == 4
    await challenges.consume(ch.id)
    assert await challenges.attempts_used(ch.id) == 0 and await challenges.get_challenge(ch.id) is None


# ── M2: an authenticator app is the only channel offered ─────────────────────────────

async def test_an_app_challenge_cannot_switch_to_email(redis) -> None:  # noqa: ANN001
    ch, code = await challenges.create_challenge(purpose="login", email="a@example.org", channel="totp",
                                                 channels=["totp"], tenant=TENANT)
    assert code is None
    with pytest.raises(FrmError) as refused:
        await challenges.resend(ch.id, "email")
    assert refused.value.code == "FRM-AUTH-1008"
    assert refused.value.details == [{"field": "channel", "message": "not_offered"}]
    assert (await challenges.get_challenge(ch.id)).channel == "totp"  # type: ignore[union-attr]
    assert challenges.describe(ch)["channels"] == ["totp"]


# ── H3: security emails through Formalie's relay, in Formalie's wording ──────────────

async def test_security_emails_skip_the_workspaces_own_mail_server(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.modules.emails import sending
    from app.modules.emails import service as emails
    from app.modules.emails import workspace

    smtp = {"mode": "smtp", "host": "mail.attacker.example", "port": 587, "security": "starttls",
            "username": "u", "password_enc": None, "from_address": "noreply@attacker.example"}
    texts: dict[str, Any] = {}

    async def route_for(db: Any, tenant_id: Any, plan_id: Any) -> dict[str, Any]:
        return dict(smtp)

    async def render(db: Any, tenant_id: Any, name: str, key: str, language: str, values: dict[str, Any],
                     **kwargs: Any) -> dict[str, str]:
        texts[key] = kwargs.get("text")
        return {"subject": "s", "html": "h", "text": "t", "from_name": "Acme", "reply_to": ""}

    async def nothing(*args: Any, **kwargs: Any) -> Any:
        return None

    async def english(*args: Any, **kwargs: Any) -> str:
        return "en"

    monkeypatch.setattr(sending, "route_for", route_for)
    monkeypatch.setattr(workspace, "render", render)
    monkeypatch.setattr(workspace, "log_sent", nothing)
    monkeypatch.setattr(workspace, "_plan", nothing)
    monkeypatch.setattr(workspace, "email_language", english)
    queued: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(emails, "queue", lambda message, *, key, values: queued.append((key, message)))

    for key in ("password_reset", "signin_code", "account_activation", "invitation", "respondent_code",
                "resume_link", "response_notification"):
        await workspace.send(None, uuid.uuid4(), "Acme", to="owner@example.org", key=key,  # type: ignore[arg-type]
                             values={"code": "123456", "link": "https://x"}, reason=key)
    routes = {key: message.get("route") for key, message in queued}
    for key in ("password_reset", "signin_code", "account_activation", "invitation", "respondent_code", "resume_link"):
        assert routes[key] is None, key  # Formalie's relay and address
    assert routes["response_notification"]["mode"] == "smtp"  # everything else keeps the workspace's choice
    default = workspace.defaults("en")["templates"]
    for key in ("password_reset", "signin_code", "account_activation", "invitation"):
        assert texts[key] == default[key], key  # the workspace's saved wording is not used
    assert texts["response_notification"] is None  # its own wording when it has one


# ── H3 and M4: what a support session may never do ───────────────────────────────────

@pytest.mark.parametrize(("method", "path", "mode", "expected"), [
    ("GET", "/settings/emails/sending", "write", "not_in_support_sessions"),
    ("PUT", "/settings/emails/sending/smtp", "write", "not_in_support_sessions"),
    ("POST", "/people", "write", "not_in_support_sessions"),
    ("POST", "/people/invites", "write", "not_in_support_sessions"),
    ("POST", "/people/0abc/invite/link", "write", "not_in_support_sessions"),
    ("PUT", "/people/signup-link", "write", "not_in_support_sessions"),
    ("POST", "/people/0abc/approve", "write", "not_in_support_sessions"),
    ("PATCH", "/people/0abc", "write", "not_in_support_sessions"),
    ("PATCH", "/roles/0abc", "write", "not_in_support_sessions"),
    ("POST", "/api-tokens", "write", "not_in_support_sessions"),
    ("POST", "/api-service/key/rotate", "write", "not_in_support_sessions"),
    ("POST", "/webhooks", "write", "not_in_support_sessions"),
    ("POST", "/datasources", "write", "not_in_support_sessions"),
    ("PATCH", "/datasources/0abc", "write", "not_in_support_sessions"),
    ("POST", "/datasources/0abc/duplicate", "write", "not_in_support_sessions"),
    ("POST", "/destinations", "write", "not_in_support_sessions"),
    ("PATCH", "/settings/security", "write", "not_in_support_sessions"),
    ("PATCH", "/settings/signin", "write", "not_in_support_sessions"),
    ("PUT", "/settings/address/domain", "write", "not_in_support_sessions"),
    ("POST", "/forms", "read", "read_only"),
    ("GET", "/people", "read", None),
    ("GET", "/settings/security", "read", None),
    ("GET", "/datasources/0abc", "read", None),
    ("POST", "/forms", "write", None),
    ("PATCH", "/settings/branding", "write", None),
    ("POST", "/datasources/0abc/explorer/rows", "write", None),
])
def test_support_refusals(method: str, path: str, mode: str, expected: str | None) -> None:
    assert support_refusal(path, method, mode) == expected


# ── M5: APP_ENV fails safe ────────────────────────────────────────────────────────────

def _prod(**changes: Any) -> Settings:
    good = {"app_env": "production", "fernet_keys": [SecretStr("k")], "id_ref_enc_key": SecretStr("e"),
            "id_ref_mac_key": SecretStr("m"), "db_app_url": SecretStr("postgresql+asyncpg://a:b@db/x"),
            "redis_url": SecretStr("redis://:pw@redis:6379/0"), "celery_result_backend": SecretStr("redis://:pw@redis:6379/1"),
            "rabbitmq_url": SecretStr("amqp://formalie:pw@mq:5672//"), "email_smtp_allow_local": False,
            "sso_allow_local": False, "datasources_allow_local": False, "webhooks_allow_local": False}
    return Settings(_env_file=None, **{**good, **changes})  # type: ignore[call-arg]


def test_app_env_defaults_to_production_and_must_be_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    unset = Settings(_env_file=None)  # type: ignore[call-arg]
    assert unset.app_env == "production" and not unset.dev_replies and not unset.is_development
    assert "APP_ENV is not set (development, test, staging or production)" in startup_problems(unset)
    with pytest.raises(UnsafeStart):
        ensure_safe_start(unset)


def test_staging_and_production_need_their_secrets() -> None:
    assert startup_problems(_prod()) == []
    assert startup_problems(_prod(app_env="staging")) == []
    problems = startup_problems(_prod(fernet_keys=[], id_ref_enc_key=None, redis_url=SecretStr("redis://127.0.0.1:6379/0"),
                                      rabbitmq_url=SecretStr("amqp://guest:guest@127.0.0.1:5672//"),
                                      webhooks_allow_local=True))
    assert problems == ["FERNET_KEYS is empty", "ID_REF_ENC_KEY is not set", "REDIS_URL has no credentials",
                        "RABBITMQ_URL uses the default guest account", "WEBHOOKS_ALLOW_LOCAL is development only"]
    assert startup_problems(_prod(app_env="development", fernet_keys=[])) == []


def test_dev_values_in_replies_only_in_development() -> None:
    assert _prod(app_env="development").dev_replies
    for env in ("test", "staging", "production"):
        assert not _prod(app_env=env).dev_replies, env
    assert _prod(app_env="test").is_development and not _prod(app_env="staging").is_development


# ── L20: single-line email settings ───────────────────────────────────────────────────

def test_email_settings_refuse_control_characters() -> None:
    from app.modules.settings.schemas import emails

    base = {"sender_name": "Acme", "reply_to": None, "footer": "Acme Ltd", "custom": {}}
    assert emails.parse(base)["sender_name"] == "Acme"
    for field, value in (("sender_name", "Acme\x00"), ("sender_name", "Ac\nme"), ("footer", "line\tone"),
                         ("reply_to", "a@example.org\x7f")):
        with pytest.raises(FrmError) as refused:
            emails.parse({**base, field: value})
        assert refused.value.code == "FRM-GEN-1002" and {"field": field, "message": "single_line"} in refused.value.details
