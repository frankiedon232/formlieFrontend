"""Settings from the environment (`.env` in development). Every variable is listed in `.env.example`."""

from __future__ import annotations

import ipaddress
import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    # ── Application ────────────────────────────────────────────────────────────
    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_release: str = "0.0.0-dev"
    api_prefix: str = "/api/v1"
    docs_enabled: bool = True
    # `python -m app.run` (uvicorn with --no-proxy-headers); certificates from mkcert in development
    server_host: str = "0.0.0.0"
    server_port: int = 5004
    ssl_certfile: str | None = r"C:\devcerts\formalie.pem"
    ssl_keyfile: str | None = r"C:\devcerts\formalie-key.pem"

    # ── Hosts and tenancy (01-ARCHITECTURE, shared/utils/tenant/host.ts) ──────
    root_domain: str = "formalie.dev"
    manage_subdomain: str = "manage"
    # Only these peers may set X-Forwarded-For / X-Forwarded-Host / CF-Connecting-IP (Nginx, the Nuxt dev proxy).
    trusted_proxies: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["127.0.0.1/32", "::1/128"])
    tenant_cache_seconds: int = 30

    # ── PostgreSQL (primary + replicas, PgBouncer) ────────────────────────────
    db_superuser_url: SecretStr | None = None  # scripts/db_bootstrap.py only, never used by the app
    db_owner_url: SecretStr | None = None  # Alembic migrations only
    db_app_url: SecretStr | None = None  # runtime, primary (NOBYPASSRLS)
    db_replica_urls: Annotated[list[SecretStr], NoDecode] = Field(default_factory=list)  # runtime, replicas
    db_relay_url: SecretStr | None = None  # outbox relay worker
    db_schema: str = "formaly"  # every workspace table lives here; global tables in `platform`; nothing in `public`
    db_test_database: str = "formalie_test"
    db_pgbouncer: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 10
    db_pool_timeout: int = 10
    db_statement_timeout_ms: int = 15_000
    db_read_your_writes_seconds: int = 5

    # ── Redis, RabbitMQ, Celery ───────────────────────────────────────────────
    redis_url: SecretStr = SecretStr("redis://127.0.0.1:6379/0")
    rabbitmq_url: SecretStr = SecretStr("amqp://guest:guest@127.0.0.1:5672//")
    celery_result_backend: SecretStr = SecretStr("redis://127.0.0.1:6379/1")
    redis_breaker_seconds: float = 15.0  # after a connection failure, skip Redis this long (fail fast)
    events_exchange: str = "formalie.events"
    outbox_relay_batch: int = 200

    # ── Secure channel, references, tokens (SECURITY-PROTOCOL) ──────────────
    # Make them with scripts/gen_keys.py. Never logged, never sent anywhere.
    id_ref_enc_key: SecretStr | None = None  # 32 bytes, base64: encrypted references (§10)
    id_ref_mac_key: SecretStr | None = None  # 32 bytes, base64: their 4-byte tag
    # Fernet keys, newest first (MultiFernet: old ones still decrypt during a rotation): CSRF and auth tokens
    fernet_keys: Annotated[list[SecretStr], NoDecode] = Field(default_factory=list)
    session_key_ttl_seconds: int = 1800  # handshake keys, sliding (§1)
    csrf_ttl_seconds: int = 7200  # §6

    # ── Email (B1: Formalie's own address; workspace domains and SMTP servers in B11) ──
    email_delivery: Literal["celery", "direct", "memory"] = "celery"  # memory: tests only
    email_from: str = "Formalie <no-reply@formalie.dev>"
    smtp_host: str = "127.0.0.1"
    smtp_port: int = 1025
    smtp_security: Literal["none", "starttls", "tls"] = "none"
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None

    # ── Social sign-in (Formalie's own app at each provider; empty = that button answers "unavailable") ──
    oauth_google_client_id: str | None = None
    oauth_google_client_secret: SecretStr | None = None
    oauth_microsoft_client_id: str | None = None
    oauth_microsoft_client_secret: SecretStr | None = None
    oauth_facebook_client_id: str | None = None
    oauth_facebook_client_secret: SecretStr | None = None
    # Where providers send people back (…/auth/oauth/{provider}/callback). Empty: https://manage.<root domain> with
    # the port the browser used (or the bare root domain when the API is called on it directly).
    oauth_redirect_base: str | None = None
    # Where emails load the Formalie mark images (the portal's public/brand). Empty: https://manage.<root domain> with
    # the port the browser used; set it when workers send (no browser port), e.g. https://manage.formalie.dev:2202.
    email_assets_url: str | None = None

    # ── Files (development: a folder; object storage before going live) and exports ──
    storage_dir: Path = ROOT_DIR / "data" / "storage"
    export_download_minutes: int = 10  # a finished export's one-time link lasts this long (mock: 10 minutes)
    export_max_rows: int = 100_000

    # ── Rate limiting (Redis sliding window) ─────────────────────────────────
    rate_limit_enabled: bool = True
    rate_limit_ip_per_minute: int = 600
    rate_limit_fail_open: bool = True  # when Redis is down: allow and log CRITICAL (False = refuse with FRM-GEN-5003)

    # ── Public form pages (B7) ────────────────────────────────────────────────
    # The Nuxt server reads published forms through /internal/* with this server-only token (NUXT_INTERNAL_TOKEN
    # there). Empty: the internal routes refuse everything.
    internal_token: SecretStr | None = None
    # Formalie's legal pages in the footer of every public form (platform settings take over in the platform admin)
    legal_terms_url: str = "https://formalie.com/terms"
    legal_privacy_url: str = "https://formalie.com/privacy"

    # ── Data sources: customers' own databases (B9) ───────────────────────────
    # Development and tests only: allow connections to this machine (loopback). Production always refuses them.
    datasources_allow_local: bool = False
    # Formalie's outgoing addresses, shown so customers can allow them in their database's firewall
    egress_ips: Annotated[list[str], NoDecode] = Field(default_factory=list)
    # Tests: "customer" databases to connect to (scripts/setup_customer_pg.py, scripts/wsl/setup-mariadb.sh)
    test_postgres_url: SecretStr | None = None
    test_mysql_url: SecretStr | None = None

    # ── Logging (BACKEND-SPEC §8) ─────────────────────────────────────────────
    log_dir: Path = ROOT_DIR / "logs"
    log_level: str = "INFO"
    log_retention_days: int = 90
    # CRITICAL lines are emailed here (comma separated); empty = no email
    alert_emails: Annotated[list[str], NoDecode] = Field(default_factory=list)
    log_console: bool = True
    # Console only (files are always JSON): readable lines, or JSON. Default: readable in development, JSON elsewhere.
    log_console_format: Literal["pretty", "json"] | None = None

    # ── Request log: every request, in full (BACKEND-SPEC §8.1, owner 2026-10-11) ──
    request_log_enabled: bool = True
    # database: the API writes batches itself · celery: through the `logs` queue · file: JSON lines only
    request_log_sink: Literal["database", "celery", "file"] = "database"
    request_log_body_max_bytes: int = 65_536  # request / response bodies kept up to this size (then truncated)
    request_log_response_bodies: Literal["none", "errors", "all"] = "errors"
    request_log_batch_size: int = 200
    request_log_flush_seconds: float = 1.0
    request_log_queue_max: int = 20_000  # in-memory; beyond this records go straight to the fallback file

    # ── GeoIP (MaxMind GeoLite2 City + ASN; Cloudflare headers are the fallback) ──
    geoip_dir: Path = ROOT_DIR / "data" / "geoip"
    maxmind_account_id: str | None = None
    maxmind_license_key: SecretStr | None = None

    @field_validator("trusted_proxies", mode="before")
    @classmethod
    def _split_proxies(cls, value: object) -> object:
        if isinstance(value, str):
            value = [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            for item in value:
                ipaddress.ip_network(item, strict=False)
        return value

    @field_validator("alert_emails", "egress_ips", mode="before")
    @classmethod
    def _split_emails(cls, value: object) -> object:
        return [item.strip() for item in value.split(",") if item.strip()] if isinstance(value, str) else value

    @field_validator("log_console_format", mode="before")
    @classmethod
    def _empty_is_default(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("log_dir", "geoip_dir", "storage_dir")
    @classmethod
    def _inside_project(cls, value: Path) -> Path:
        # A relative path in .env means inside this project, wherever the server is started from.
        return value if value.is_absolute() else ROOT_DIR / value

    @field_validator("db_schema")
    @classmethod
    def _plain_identifier(cls, value: str) -> str:
        # Used inside SQL (migrations, search_path), so only a plain lower-case identifier is accepted.
        if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", value) or value in ("public", "platform"):
            raise ValueError("DB_SCHEMA must be a lower-case identifier other than public and platform")
        return value

    @field_validator("fernet_keys", mode="before")
    @classmethod
    def _split_fernet_keys(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("db_replica_urls", mode="before")
    @classmethod
    def _split_replicas(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_development(self) -> bool:
        return self.app_env in ("development", "test")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
