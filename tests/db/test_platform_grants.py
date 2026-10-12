"""CI guard for the platform admin's database roles (B16, PLATFORM-ADMIN-INTEGRATION §1):

- platform_reader reads every table of both schemas but never a secret (`*_hash`, `*_enc`) or answer column, and
  writes nothing;
- platform_writer inserts and updates the global tables only, deletes nothing, reads no workspace table;
- a write by platform_writer must name the staff member (the trigger stamps published_at);
- formalie_app reads the global tables and never writes them.
A migration that adds a secret column or a table without these rules fails here.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest

from app.core.config import get_settings
from app.modules.platform_bridge.grants import B16_GLOBAL_TABLES, HIDDEN, WRITER_TABLES, is_hidden

pytestmark = pytest.mark.db

S = get_settings().db_schema
TABLES = """
    SELECT n.nspname, c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname IN (%s, 'platform') AND c.relkind IN ('r', 'p') AND NOT c.relispartition ORDER BY 1, 2
"""


def _tables(owner: psycopg.Connection) -> list[tuple[str, str]]:
    return [(r[0], r[1]) for r in owner.execute(TABLES, (S,)).fetchall()]


def _columns(owner: psycopg.Connection, schema: str, table: str) -> list[str]:
    return [r[0] for r in owner.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s",
        (schema, table)).fetchall()]


def test_platform_reader_reads_everything_but_secrets_and_answers(owner: psycopg.Connection) -> None:
    problems = []
    readable = 0
    for schema, table in _tables(owner):
        if owner.execute("SELECT has_table_privilege('platform_reader', %s, 'SELECT')", (f"{schema}.{table}",)).fetchone()[0]:
            problems.append(f"{schema}.{table}: table-wide SELECT (must be column by column)")
        for column in _columns(owner, schema, table):
            can = owner.execute("SELECT has_column_privilege('platform_reader', %s, %s, 'SELECT')",
                                (f"{schema}.{table}", column)).fetchone()[0]
            if is_hidden(table, column) and can:
                problems.append(f"{schema}.{table}.{column}: secret or answer readable")
            elif not is_hidden(table, column) and not can:
                problems.append(f"{schema}.{table}.{column}: not readable")
            readable += can
    assert not problems, "\n".join(problems)
    assert readable > 500
    for table, columns in HIDDEN.items():  # every listed table still exists with its hidden columns
        for column in columns:
            assert column in _columns(owner, S if table not in ("tenants",) else "platform", table), (table, column)


def test_platform_reader_writes_nothing(owner: psycopg.Connection) -> None:
    for schema, table in _tables(owner):
        for privilege in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
            assert not owner.execute("SELECT has_table_privilege('platform_reader', %s, %s)",
                                     (f"{schema}.{table}", privilege)).fetchone()[0], (schema, table, privilege)


def test_platform_writer_writes_the_global_tables_only(owner: psycopg.Connection) -> None:
    tables = _tables(owner)
    assert {("platform", t) for t in WRITER_TABLES} <= set(tables)
    for schema, table in tables:
        qualified = f"{schema}.{table}"
        global_ = schema == "platform" and table in WRITER_TABLES
        for privilege in ("INSERT", "UPDATE"):
            can = owner.execute("SELECT has_table_privilege('platform_writer', %s, %s)", (qualified, privilege)).fetchone()[0]
            assert can == global_, (qualified, privilege)
        assert not owner.execute("SELECT has_table_privilege('platform_writer', %s, 'DELETE')", (qualified,)).fetchone()[0]
        if schema == S:
            assert not owner.execute("SELECT has_table_privilege('platform_writer', %s, 'SELECT')", (qualified,)).fetchone()[0]


def test_the_app_reads_global_tables_and_never_writes_them(owner: psycopg.Connection) -> None:
    for table in B16_GLOBAL_TABLES:
        qualified = f"platform.{table}"
        assert owner.execute("SELECT has_table_privilege('formalie_app', %s, 'SELECT')", (qualified,)).fetchone()[0]
        for privilege in ("INSERT", "UPDATE", "DELETE"):
            assert not owner.execute("SELECT has_table_privilege('formalie_app', %s, %s)",
                                     (qualified, privilege)).fetchone()[0], (table, privilege)


def test_a_platform_write_names_the_staff_member(superuser: psycopg.Connection) -> None:
    key = f"test_flag_{uuid.uuid4().hex[:8]}"
    staff = uuid.uuid4()
    with superuser.transaction():
        superuser.execute("SET LOCAL ROLE platform_writer")
        with pytest.raises(psycopg.errors.NotNullViolation), superuser.transaction():
            superuser.execute("INSERT INTO platform.feature_flags (key, enabled) VALUES (%s, true)", (key,))
        superuser.execute("INSERT INTO platform.feature_flags (key, enabled, published_by_staff_id) VALUES (%s, true, %s)",
                          (key, staff))
        row = superuser.execute("SELECT published_at, published_by_staff_id FROM platform.feature_flags WHERE key = %s",
                                (key,)).fetchone()
        assert row[0] is not None and row[1] == staff
        superuser.execute("UPDATE platform.feature_flags SET retired_at = now(), published_by_staff_id = %s "
                          "WHERE key = %s", (staff, key))
        with pytest.raises(psycopg.errors.InsufficientPrivilege), superuser.transaction():
            superuser.execute("DELETE FROM platform.feature_flags WHERE key = %s", (key,))
        with pytest.raises(psycopg.errors.InsufficientPrivilege), superuser.transaction():
            superuser.execute(f"UPDATE {S}.users SET first_name = 'x' WHERE false")


def test_shipped_rows_are_there(owner: psycopg.Connection) -> None:
    counts = {t: owner.execute(f"SELECT count(*) FROM platform.{t}").fetchone()[0] for t in B16_GLOBAL_TABLES}
    assert counts["platform_settings"] >= 4 and counts["reserved_subdomains"] >= 20 and counts["plans"] == 4
    assert counts["plan_prices"] == 9 and counts["plan_limits"] == 4 and counts["plan_features"] > 40
    assert counts["system_email_templates"] >= 13 * 20 and counts["system_templates"] >= 80
    assert counts["system_option_lists"] == 6 and counts["system_option_items"] > 50
    assert counts["system_themes"] >= 10 and counts["system_page_designs"] >= 4
    shipped_only = {t: owner.execute(f"SELECT count(*) FROM platform.{t} WHERE published_by_staff_id IS NULL").fetchone()[0]
                    for t in ("feature_flags", "announcements", "system_folders")}
    assert shipped_only == {"feature_flags": 0, "announcements": 0, "system_folders": 0}  # none shipped
    shipped = owner.execute("SELECT count(*) FROM platform.platform_settings WHERE published_by_staff_id IS NULL").fetchone()[0]
    assert shipped == counts["platform_settings"]
