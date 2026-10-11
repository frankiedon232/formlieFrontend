"""A PostgreSQL "customer" database on this machine for trying and testing data sources (B9): a login role
`formalie_customer` that owns `customer_dev` and `customer_test`, like a customer's own application account.
Development only. Writes TEST_POSTGRES_URL into .env (the password is never printed). Safe to run again.

    fmly\\Scripts\\python.exe scripts\\setup_customer_pg.py
"""

from __future__ import annotations

import re
import secrets
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.core.config import get_settings  # noqa: E402

ROLE = "formalie_customer"
DATABASES = ("customer_dev", "customer_test")


def main() -> None:
    settings = get_settings()
    if settings.is_production:
        raise SystemExit("Development only.")
    if settings.db_superuser_url is None:
        raise SystemExit("DB_SUPERUSER_URL is not set in .env.")
    url = make_url(settings.db_superuser_url.get_secret_value())
    password = secrets.token_urlsafe(24)
    conninfo = dict(host=url.host or "127.0.0.1", port=url.port or 5432, user=url.username, password=url.password,
                    dbname=url.database or "postgres", autocommit=True)
    with psycopg.connect(**conninfo) as conn:
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ROLE,)).fetchone()
        statement = "ALTER ROLE {} LOGIN PASSWORD {}" if exists else "CREATE ROLE {} LOGIN PASSWORD {}"
        conn.execute(sql.SQL(statement).format(sql.Identifier(ROLE), sql.Literal(password)))
        for name in DATABASES:
            if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
                conn.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(name), sql.Identifier(ROLE)))
    # formalie.dev resolves to this machine: a name the field checks accept (loopback needs DATASOURCES_ALLOW_LOCAL)
    line = f"TEST_POSTGRES_URL=postgresql://{ROLE}:{password}@formalie.dev:{url.port or 5432}/customer_test"
    env = ROOT / ".env"
    text = env.read_text(encoding="utf-8") if env.exists() else ""
    if re.search(r"^TEST_POSTGRES_URL=.*$", text, re.MULTILINE):
        text = re.sub(r"^TEST_POSTGRES_URL=.*$", line, text, flags=re.MULTILINE)
    else:
        text = text.rstrip("\n") + f"\n{line}\n"
    if not re.search(r"^DATASOURCES_ALLOW_LOCAL=", text, re.MULTILINE):
        text = text.rstrip("\n") + "\nDATASOURCES_ALLOW_LOCAL=true\n"
    env.write_text(text, encoding="utf-8")
    print(f"Role {ROLE} owns {', '.join(DATABASES)}; TEST_POSTGRES_URL written to .env (password not shown).")


if __name__ == "__main__":
    main()
