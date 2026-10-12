"""Refuse to start unsafely (security review M5). Checked when the API or the gateway starts (their lifespan), not
when settings are read, so scripts and tests can still build settings freely.

- APP_ENV must be set explicitly (unset means production, see config.py).
- Staging and production need their own secrets: Fernet keys, the reference keys, the database URL, and Redis and
  RabbitMQ with credentials (not the development defaults), and none of the development-only `*_ALLOW_LOCAL`
  switches.
"""

from __future__ import annotations

from app.core.config import Settings

DEV_DEFAULT_URLS = {"redis_url": "redis://127.0.0.1:6379/0", "celery_result_backend": "redis://127.0.0.1:6379/1"}
LOCAL_SWITCHES = ("email_smtp_allow_local", "sso_allow_local", "datasources_allow_local", "webhooks_allow_local")


class UnsafeStart(RuntimeError):
    pass


def startup_problems(settings: Settings) -> list[str]:
    """What stops this server from starting, as setting names with the reason (never their values)."""
    problems: list[str] = []
    if "app_env" not in settings.model_fields_set:
        problems.append("APP_ENV is not set (development, test, staging or production)")
    if settings.app_env not in ("staging", "production"):
        return problems
    if not settings.fernet_keys:
        problems.append("FERNET_KEYS is empty")
    for name in ("id_ref_enc_key", "id_ref_mac_key", "db_app_url"):
        if getattr(settings, name) is None:
            problems.append(f"{name.upper()} is not set")
    for name, default in DEV_DEFAULT_URLS.items():
        value = getattr(settings, name).get_secret_value()
        if value == default or "@" not in value:
            problems.append(f"{name.upper()} has no credentials")
    rabbit = settings.rabbitmq_url.get_secret_value()
    if "guest:guest@" in rabbit or "@" not in rabbit:
        problems.append("RABBITMQ_URL uses the default guest account")
    for name in LOCAL_SWITCHES:
        if getattr(settings, name):
            problems.append(f"{name.upper()} is development only")
    return problems


def ensure_safe_start(settings: Settings) -> None:
    problems = startup_problems(settings)
    if problems:
        raise UnsafeStart(f"Formalie will not start ({settings.app_env}): " + "; ".join(problems))
