"""Records the frontend's query editor and explorer rules (B9) into tests/vectors/sql_rules.json: splitting scripts,
the statement at the cursor, what a statement does, the tables and parameters it names, "Format", structure changes
per engine, export formats, typed values and activity kinds (shared/utils/datasources/sql.ts, ddl.ts,
exportFormats.ts, values.ts, activity.ts).

    fmly\\Scripts\\python.exe scripts\\dump_sql_rules.py [path\\to\\formalieFrontend]

tests/parity/test_sql_rules.py holds the port (app/modules/data_sources/sql.py, ddl.py, tables.py) to these answers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "sql_rules.json"

ENTRY = r"""
import * as S from '__SHARED__/utils/datasources/sql.ts'
import * as D from '__SHARED__/utils/datasources/ddl.ts'
import * as F from '__SHARED__/utils/datasources/exportFormats.ts'
import * as V from '__SHARED__/utils/datasources/values.ts'
import * as A from '__SHARED__/utils/datasources/activity.ts'

const engines = ['mysql', 'mariadb', 'postgresql', 'sqlserver', 'oracle']
const scripts = [
  'SELECT 1', 'select * from clients;', 'SELECT 1; SELECT 2;', '  \n -- only a comment\n ', '/* block */ SELECT a FROM b; -- tail',
  "SELECT 'a;b' FROM t; UPDATE t SET x = 'it''s;' WHERE id = 1", 'SELECT "we;ird" FROM `x;y`; DELETE FROM [a;b] WHERE c = 1;',
  'CREATE FUNCTION f() RETURNS int AS $$ SELECT 1; $$ LANGUAGE sql; SELECT f();', 'SELECT $tag$ ; $tag$; SELECT 2',
  'WITH x AS (SELECT 1) SELECT * FROM x', 'WITH d AS (DELETE FROM t RETURNING *) SELECT * FROM d', 'SELECT * INTO new_t FROM t',
  'insert into public.clients (a, b) values (1, 2)', 'MERGE INTO t USING s ON t.id = s.id', 'UPSERT INTO t VALUES (1)', 'REPLACE INTO t VALUES (1)',
  'update clients set phone = :phone where id = :id', 'delete from "Intake"."Cases" where id = :id', 'TRUNCATE TABLE x', 'alter table x add column y int',
  'drop table if exists x', 'GRANT SELECT ON t TO u', 'SHOW TABLES', 'EXPLAIN SELECT 1', 'DESCRIBE t', 'VALUES (1), (2)', 'TABLE clients', 'VACUUM',
  '(SELECT 1) UNION (SELECT 2)', 'SELECT a::text, :p1, :p2, :p1 FROM t WHERE b = :p2 AND c = \'::nope :inside\' -- :comment\n AND d = :p3',
  'SELECT * FROM a JOIN b ON a.id = b.a_id LEFT JOIN "c d" . "e" ON 1=1 WHERE x IN (SELECT y FROM z)', 'SELECT 😀, \'é\' FROM t; SELECT 2 😀;',
  'select a, b, count(*) as n from t where a = 1 and b between 1 and 2 or c is null group by a, b having count(*) > 1 order by n desc limit 10 offset 5',
  "insert into t (a, b) values (1, 'x'), (2, 'y') returning id", 'update t set a = 1, b = 2 where id in (1, 2, 3)',
  'select distinct a from t', 'select top 5 * from t', 'select case when a > 1 then \'x\' else \'y\' end from t', 'select * from t -- note\nwhere a = 1',
  'SELECT a FROM t1 INNER JOIN t2 ON t1.id = t2.id AND t1.x = t2.x FULL OUTER JOIN t3 ON 1 = 1', 'select coalesce(a, 0)::int from t',
  'select * from t where (a = 1 or b = 2) and not exists (select 1 from u where u.id = t.id)', 'SELECT x FROM y FETCH FIRST 10 ROWS ONLY',
  "SELECT 'unterminated", 'SELECT /* unterminated', 'SELECT [unterminated', 'select a||b, a <> b, a != b, a <= b from t', 'select f(a)(b) from t',
  'DELETE FROM t', 'select * from t where a = 1;;; select 2', 'select\n  a,\n  b\nfrom\n  t', 'SELECT 1.5, 2, .5, 3e2 FROM dual',
]
const split = scripts.map(sql => ({ sql, statements: S.splitStatements(sql), kind: S.scriptKind(sql), format: /[\uD800-\uDFFF]/.test(sql) ? null : S.formatSql(sql) }))
const statements = scripts.flatMap(sql => S.splitStatements(sql).map(s => ({ text: s.text, kind: S.statementKind(s.text), tables: S.tablesIn(s.text), params: S.parametersIn(s.text), code: /[\uD800-\uDFFF]/.test(s.text) ? null : S.codeOnly(s.text) })))
const cursors = []
for (const sql of scripts) for (let c = 0; c <= sql.length + 1; c += Math.max(1, Math.floor(sql.length / 7))) cursors.push({ sql, cursor: c, at: S.statementAt(sql, c) })

const specs = [
  { name: 'id', kind: 'integer', nullable: false, primary: true, auto: true }, { name: 'big', kind: 'big_integer', nullable: false, primary: true, auto: true },
  { name: 'title', kind: 'text', length: 120, nullable: false, default: "it's" }, { name: 'body', kind: 'long_text', nullable: true },
  { name: 'price', kind: 'decimal', length: 10, scale: 3, nullable: true, default: '9.5' }, { name: 'amount', kind: 'decimal', nullable: true },
  { name: 'ok', kind: 'boolean', nullable: false, default: 'true' }, { name: 'day', kind: 'date', nullable: true, default: '2026-10-11' },
  { name: 'at', kind: 'datetime', nullable: true, default: '2026-10-11T08:00:00.000Z' }, { name: 'clock', kind: 'time', nullable: true },
  { name: 'meta', kind: 'json', nullable: true, default: '{"a":1}' }, { name: 'plain', kind: 'text', nullable: true, length: 0 },
  { name: 'n', kind: 'integer', nullable: true, primary: false, auto: true }, { name: 'slash', kind: 'text', nullable: true, default: 'a\\b' },
]
const ddl = engines.map(engine => ({
  engine,
  kinds: D.kindsFor(engine),
  types: specs.map(spec => D.typeFor(engine, spec)),
  columns: specs.map(spec => D.columnSql(engine, 'people', spec)),
  create: D.createTableStatements(engine, 'app', 'people', specs.slice(0, 1).concat(specs.slice(2))),
  createTwoKeys: D.createTableStatements(engine, 'app', 'pairs', [{ ...specs[0], auto: false }, { ...specs[2], primary: true }]),
  changes: [
    { op: 'add_column', column: specs[2] }, { op: 'drop_column', column: 'body' }, { op: 'rename_table', name: 'persons' },
    { op: 'add_index', name: 'people_title_idx', columns: ['title', 'day'], unique: false }, { op: 'add_index', name: 'u', columns: ['title'], unique: true },
    { op: 'drop_index', name: 'people_title_idx' }, { op: 'truncate' }, { op: 'drop_table' },
    { op: 'alter_column', column: 'title', to: { name: 'heading', kind: 'text', length: 200, nullable: true } },
    { op: 'alter_column', column: 'title', to: { name: 'title', kind: 'text', length: 120, nullable: false, default: "it's" } },
    { op: 'alter_column', column: 'price', to: { name: 'price', kind: 'decimal', length: 12, scale: 2, nullable: false, default: '1' } },
  ].map(change => ({ change, current: { name: 'title', type: 'VARCHAR(120)', nullable: false, default: "it's", primary: false },
    out: D.changeStatements(engine, 'app', 'people', change, { name: 'title', type: 'VARCHAR(120)', nullable: false, default: "it's", primary: false }),
    none: D.changeStatements(engine, 'app', 'people', change) })),
}))
const types = ['VARCHAR(120)', 'TEXT', 'INTEGER', 'BIGINT', 'NUMBER(19)', 'NUMERIC(10, 2)', 'NUMBER(12,3)', 'DECIMAL', 'BOOLEAN', 'DATE', 'TIMESTAMPTZ', 'TIME', 'JSONB', 'CLOB', 'UUID', 'NVARCHAR(MAX)', 'TINYINT(1)', 'BIT', 'FLOAT']
const specOf = types.map(type => ({ type, spec: D.specOfType(type) }))
const risky = types.flatMap(type => specs.map(spec => ({ from: type, to: { kind: spec.kind, length: spec.length ?? null, scale: spec.scale ?? null }, risky: D.typeChangeRisky(type, spec) })))
const names = ['', 'clients', 'Clients_2', '2clients', 'my table', 'formalie_x', 'Form_y', 'fmly_', 'x'.repeat(63), 'x'.repeat(64), 'x'.repeat(129), 'ñame', 'a-b']
const checks = engines.flatMap(engine => names.flatMap(name => ['table', 'column', 'index'].map(what => ({ engine, name, what, problem: D.checkName(engine, name, what) }))))
const normal = engines.flatMap(engine => ['  My  Table ', 'Ünï cødé', 'a\tb'].map(text => ({ engine, text, out: D.normaliseDbName(engine, text) })))
const values = [null, undefined, '', 'text', "it's", 'back\\slash', 0, 1, 2.5, -3, '1', 'true', 'TRUE', 'no', true, false, '2026-10-11', '2026-10-11T08:09:10.123Z', '2026-10-11T08:09:10+02:00', { a: [1, 'x'] }, [1, 2], 'NaN', 'abc']
const litTypes = ['INTEGER', 'NUMERIC(10,2)', 'BOOLEAN', 'TINYINT(1)', 'DATE', 'TIMESTAMPTZ', 'DATETIME(3)', 'JSONB', 'JSON', 'VARCHAR(10)', 'TEXT']
const enc = v => (v === undefined ? '__undefined__' : v)
const literals = engines.flatMap(engine => litTypes.flatMap(type => values.map(value => ({ engine, type, value: enc(value), out: F.sqlLiteral(engine, type, value) }))))
const exportColumns = [{ name: 'id', type: 'INTEGER', primary: true, has_default: true }, { name: 'name', type: 'VARCHAR(100)' }, { name: 'meta', type: 'JSONB' }, { name: 'ok', type: 'BOOLEAN' }, { name: 'at', type: 'TIMESTAMPTZ' }]
const exportRows = [{ id: 1, name: "O'Brien", meta: '{"a":[1,2],"b":{"c":null}}', ok: true, at: '2026-10-11T08:00:00.000Z' }, { id: 2, name: null, meta: 'not json', ok: false }, { id: 3, name: 'x\\y', meta: { already: 1.5 }, ok: null, at: null }, {}]
const jsonOut = F.jsonExport(exportColumns, exportRows)
const scriptsOut = engines.map(engine => ({ engine, out: F.sqlInsertScript(engine, { schema: 'app', table: 'people' }, exportColumns, exportRows, new Date('2026-10-11T08:00:00.000Z')) }))
const parseCols = ['INTEGER', 'BIGINT', 'NUMERIC(10,2)', 'BOOLEAN', 'DATE', 'TIMESTAMPTZ', 'TIME', 'JSONB', 'VARCHAR(5)', 'TEXT'].flatMap(type => [{ type, nullable: true, has_default: false }, { type, nullable: false, has_default: false }, { type, nullable: false, has_default: true }])
const raws = [null, undefined, '', '  ', '12', ' 12 ', '12.5', '1 000', 'abc', 0, 7, 7.5, true, false, 'yes', 'Off', 'Y', 'maybe', '2026-10-11', '2026-02-30', '2026-13-01', '2026-10-11T08:09:10Z',
  '2026-10-11T08:09:10.5+02:00', '2026-10-11T08:09', '12:30', '12:30:45', '1:30', '{"a":1}', '[1,2]', 'NaN', '{bad', { x: 1 }, [1], 'abcdef', 'abcde', 'é😀abc', '0x1F', '1e3', 'Infinity']
const parsed = parseCols.flatMap(column => raws.map(raw => ({ column, raw: enc(raw), out: V.parseValue(column, raw) })))
const activity = ['data.query_run', 'data.row_updated', 'data.table_dropped', 'data.query_exported', 'data.column_added', 'data.credentials_changed', 'forms.created', 'nope'].map(action => ({ action, kind: A.kindOfAction(action) }))
process.stdout.write(JSON.stringify({ about: 'Recorded from the frontend by scripts/dump_sql_rules.py. Do not edit.', split, statements, cursors, ddl, specs, specOf, risky, checks, normal, literals, exportColumns, exportRows, jsonOut, scriptsOut, parsed, activity, actions: A.ACTIVITY_ACTIONS }))
"""


def main() -> None:
    result = run_in_node(ENTRY, {})
    OUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(result['statements'])} statements, {len(result['cursors'])} cursors, "
          f"{len(result['literals'])} literals, {len(result['parsed'])} values")


if __name__ == "__main__":
    main()
