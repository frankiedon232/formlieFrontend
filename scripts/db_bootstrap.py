"""Creates the DB roles and the databases once per cluster (idempotent; re-run to change passwords).

    fmly\\Scripts\\python.exe scripts\\db_bootstrap.py

Reads .env: DB_SUPERUSER_URL (e.g. the `postgres` account), and the user + password of DB_OWNER_URL, DB_APP_URL and
DB_RELAY_URL. Creates the database named in DB_APP_URL and DB_TEST_DATABASE, both owned by formalie_owner.
Then run migrations: `alembic upgrade head` and `alembic -x db=test upgrade head`.

Roles (DATABASE-DESIGN → DB roles, BACKEND-SPEC §2):
  formalie_owner     LOGIN                  owns the schema, migrations only
  formalie_app       LOGIN NOBYPASSRLS      the API and per-workspace workers; no DELETE on tenant tables
  formalie_worker    LOGIN BYPASSRLS        outbox relay and partition upkeep; privileges on those only
  formalie_readonly  NOLOGIN                reporting on replicas (LOGIN set when reporting starts)
  platform_reader    NOLOGIN BYPASSRLS      the platform admin on the replica (LOGIN in B16)
  platform_writer    NOLOGIN                the platform admin on global tables (LOGIN in B16)
"""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402


def _creds(url_secret: object, label: str) -> tuple[str, str, str]:
    if url_secret is None:
        raise SystemExit(f"{label} is not set in .env")
    url = make_url(url_secret.get_secret_value())  # type: ignore[attr-defined]
    if not url.username or not url.password:
        raise SystemExit(f"{label} needs a user name and a password")
    return url.username, url.password, url.database or "formalie"


def _ensure_role(cur: psycopg.Cursor, name: str, options: str, password: str | None) -> None:
    exists = cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (name,)).fetchone()
    verb = "ALTER" if exists else "CREATE"
    statement = sql.SQL(f"{verb} ROLE {{}} WITH {options}").format(sql.Identifier(name))
    if password is not None:
        statement = statement + sql.SQL(" PASSWORD {}").format(sql.Literal(password))
    cur.execute(statement)
    print(f"  role {name}: {'updated' if exists else 'created'}")


def main() -> None:
    settings = get_settings()
    if settings.db_superuser_url is None:
        raise SystemExit("DB_SUPERUSER_URL is not set in .env")
    owner, owner_pw, database = _creds(settings.db_owner_url, "DB_OWNER_URL")
    app_user, app_pw, _ = _creds(settings.db_app_url, "DB_APP_URL")
    worker, worker_pw, _ = _creds(settings.db_relay_url, "DB_RELAY_URL")
    expected = {"DB_OWNER_URL": (owner, "formalie_owner"), "DB_APP_URL": (app_user, "formalie_app"),
                "DB_RELAY_URL": (worker, "formalie_worker")}
    for label, (actual, wanted) in expected.items():
        if actual != wanted:
            raise SystemExit(f"{label} must connect as {wanted} (migrations grant to that name), not {actual}")

    superuser = make_url(settings.db_superuser_url.get_secret_value())
    dsn = superuser.set(drivername="postgresql").render_as_string(hide_password=False)
    with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
        print("Roles")
        _ensure_role(cur, "formalie_owner", "LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS", owner_pw)
        _ensure_role(cur, "formalie_app", "LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS", app_pw)
        _ensure_role(cur, "formalie_worker", "LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE BYPASSRLS", worker_pw)
        _ensure_role(cur, "formalie_readonly", "NOLOGIN NOSUPERUSER NOBYPASSRLS", None)
        _ensure_role(cur, "platform_reader", "NOLOGIN NOSUPERUSER BYPASSRLS", None)
        _ensure_role(cur, "platform_writer", "NOLOGIN NOSUPERUSER NOBYPASSRLS", None)
        cur.execute("ALTER ROLE platform_reader SET default_transaction_read_only = on")
        cur.execute("ALTER ROLE platform_reader SET statement_timeout = '15s'")
        cur.execute("ALTER ROLE formalie_readonly SET default_transaction_read_only = on")

        print("Databases")
        for name in (database, settings.db_test_database):
            exists = cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
            if not exists:
                cur.execute(sql.SQL("CREATE DATABASE {} OWNER formalie_owner ENCODING 'UTF8' TEMPLATE template0")
                            .format(sql.Identifier(name)))
            cur.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(name)))
            cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO formalie_app, formalie_worker, formalie_readonly, "
                                "platform_reader, platform_writer").format(sql.Identifier(name)))
            # Default search_path per role and database, so it holds through PgBouncer too.
            for role in ("formalie_owner", "formalie_app", "formalie_worker", "formalie_readonly",
                         "platform_reader", "platform_writer"):
                cur.execute(sql.SQL("ALTER ROLE {} IN DATABASE {} SET search_path = {}, platform").format(
                    sql.Identifier(role), sql.Identifier(name), sql.Identifier(settings.db_schema)))
            print(f"  database {name}: {'exists' if exists else 'created'} (schema {settings.db_schema})")
    print("Done. Next: alembic upgrade head  and  alembic -x db=test upgrade head")


if __name__ == "__main__":
    main()
