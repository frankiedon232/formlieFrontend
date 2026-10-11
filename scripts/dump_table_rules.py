"""Records the frontend's response table rules (B9) into tests/vectors/table_rules.json: table and column names, the
part after the prefix, types per field and engine, the columns of a new table, the SQL Formalie runs, matching an
existing table, checking a mapping and a response as a row (shared/utils/datasources/tables.ts, values.ts).

    fmly\\Scripts\\python.exe scripts\\dump_table_rules.py [path\\to\\formalieFrontend]

tests/parity/test_table_rules.py holds the port (app/modules/data_sources/tables.py) to these answers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "table_rules.json"

ENTRY = r"""
import * as T from '__SHARED__/utils/datasources/tables.ts'
import * as V from '__SHARED__/utils/datasources/values.ts'
import { FIELD_TYPE_KEYS } from '__SHARED__/utils/forms/fields.ts'

const engines = ['mysql', 'mariadb', 'postgresql', 'sqlserver', 'oracle']
const texts = ['Customer Onboarding', 'Café Crème', 'firstName', 'HTTPServer', '2026 survey', '  __x__  ', '', '日本語', 'Ünïcödé Straße', 'select', 'user', 'a-b-c',
  'x'.repeat(80), 'Kontakt 😀 form', 'İstanbul', 'ﬁle', 'ＡＢＣ', 'order', 'response_id', 'Ω', 'abc123DEF', 'A1b2', '_', '9']
const prefixes = ['formalie_', 'fm_', '', 'very_long_prefix_' + 'p'.repeat(40)]
const names = []
for (const engine of engines) {
  for (const text of texts) {
    names.push({ engine, text, snake: T.snake(text), tables: prefixes.map(p => T.tableNameFor(engine, p, text)) })
  }
  const taken = new Set()
  const keys = ['email', 'email', 'Email', 'select', 'select_value', '', '日本', 'x'.repeat(200), 'x'.repeat(200), 'first_name', 'firstName']
  names.push({ engine, keys, columns: keys.map(k => T.columnNameFor(engine, k, taken)), taken: [...taken] })
}
const rests = ['', 'abc', 'abcdef', 'ab cdef', 'abc-def', 'ABCDEF_1', 'x'.repeat(70), 'x'.repeat(130), 'ñandúes', 'abcdef\n']
const restChecks = engines.flatMap(engine => prefixes.flatMap(prefix => rests.map(rest => ({ engine, prefix, rest, problem: T.checkTableRest(engine, prefix, rest), max: T.tableRestMax(engine, prefix) }))))
const normalised = engines.flatMap(engine => ['My Table', ' two  spaces ', 'Tab\there', 'nbsp x', 'Ünï'].map(text => ({ engine, text, out: T.normaliseTableRest(engine, text) })))

const opts = [{ value: 'a', label: 'Apple' }, { value: 'b', label: 'Banana' }, { value: '3', label: 'Three' }]
const fields = FIELD_TYPE_KEYS.map((type, i) => ({ key: `f_${type}`, label: `Question ${i} ${type}`, type, options: opts }))
const plain = FIELD_TYPE_KEYS.map(type => ({ key: `p_${type}`, label: '', type }))
const types = engines.flatMap(engine => ['json', 'text'].map(multi => ({ engine, multi, types: FIELD_TYPE_KEYS.map(type => T.columnTypeFor(engine, { type }, multi)),
  meta: ['response_id', 'submitted_at', 'form_version', 'language', 'response_number', 'respondent_email', 'review_status'].map(m => T.metaTypeFor(engine, m)) })))
const forms = engines.flatMap(engine => ['json', 'text'].map(multi => {
  const columns = T.columnsForForm(engine, fields, { multi_value: multi })
  const extra = T.columnsForForm(engine, plain.slice(0, 5), { multi_value: multi }, ['response_id', 'submitted_at', 'response_number', 'review_status', 'respondent_email'])
  const messed = columns.map((c, i) => ({ ...c, type: 'WRONG', source: i % 7 === 3 ? null : i % 11 === 5 ? { kind: 'field', key: 'gone' } : c.source }))
  return { engine, multi, columns, extra, typed: T.typedForEngine(engine, messed, fields, multi === 'json' ? 'text' : 'json'), messed }
}))
const sql = forms.filter(f => f.multi === 'json').flatMap(({ engine, columns }) => [['public', 'formalie_onboarding'], ['', 'fm_x'], ['we"ird`s]', 'ta"b`l]e'], ['APP', 'X'.repeat(130)]].map(([schema, table]) => {
  const labels = new Map(fields.map((f, i) => [f.key, i % 5 === 0 ? 'Same label' : i % 5 === 1 ? '  ' : i % 5 === 2 ? 'Q "quoted" [x] `y`' : i % 5 === 3 ? 'Très long ' + 'é'.repeat(140) : f.label]))
  return { engine, schema, table, columns, create: T.createTableSql(engine, schema, table, columns), index: T.indexSql(engine, schema, table, 'submitted_at'),
    add: T.addColumnSql(engine, schema, table, columns[5]), unique: T.uniqueKeySql(engine, schema, table, 'response_id'),
    labels: [...labels], view: T.viewSql(engine, schema, table, columns, labels), standard: T.standardSettings({ write_mode: 'insert', key_column: 'x', multi_value: 'json', choices: 'value' }, columns),
    standardNone: T.standardSettings({ write_mode: 'insert', key_column: 'x' }, columns.slice(2)) }
}))
const tableColumns = [
  { name: 'submission_id', type: 'VARCHAR(64)', nullable: false, has_default: false, primary: true, unique: true },
  { name: 'Full_Name', type: 'VARCHAR(200)', nullable: true, has_default: false, primary: false, unique: false },
  { name: 'email', type: 'VARCHAR(320)', nullable: true, has_default: false, primary: false, unique: false },
  { name: 'phone', type: 'VARCHAR(40)', nullable: true, has_default: false, primary: false, unique: false },
  { name: 'Message', type: 'TEXT', nullable: false, has_default: false, primary: false, unique: false },
  { name: 'received_at', type: 'TIMESTAMP', nullable: false, has_default: true, primary: false, unique: false },
  { name: 'created_at', type: 'TIMESTAMP', nullable: true, has_default: false, primary: false, unique: false },
  { name: 'status', type: 'VARCHAR(16)', nullable: true, has_default: false, primary: false, unique: false },
  { name: 'lang', type: 'CHAR(2)', nullable: true, has_default: false, primary: false, unique: false },
  { name: 'budget', type: 'NUMERIC(10,2)', nullable: true, has_default: false, primary: false, unique: false },
  { name: 'agree', type: 'BOOLEAN', nullable: true, has_default: false, primary: false, unique: false },
  { name: 'extra', type: 'JSONB', nullable: true, has_default: false, primary: false, unique: false },
  { name: 'unrelated', type: 'INT', nullable: false, has_default: false, primary: false, unique: false },
]
const leadFields = [{ key: 'full_name', label: 'Full name', type: 'short_text' }, { key: 'e', label: 'Email', type: 'email' }, { key: 'message', label: 'Your message', type: 'long_text' },
  { key: 'phone', label: 'Phone', type: 'phone' }, { key: 'budget', label: null, type: 'text' }, { key: 'agree', label: 'Agree', type: 'consent' }, { key: 'extra', label: 'Extra', type: 'checkbox' }]
const matched = [
  { columns: tableColumns, fields: leadFields, out: T.matchColumns(tableColumns, leadFields) },
  { columns: tableColumns, fields: fields.slice(0, 20), out: T.matchColumns(tableColumns, fields.slice(0, 20)) },
  { columns: tableColumns.slice(1), fields: [], out: T.matchColumns(tableColumns.slice(1), []) },
]
const settingsList = [{ write_mode: 'insert', key_column: 'response_id', multi_value: 'json', choices: 'value' }, { write_mode: 'upsert', key_column: 'response_id', multi_value: 'text', choices: 'label' },
  { write_mode: 'upsert', key_column: 'nope', multi_value: 'json', choices: 'label' }, { write_mode: 'upsert', key_column: 'submission_id', multi_value: 'text', choices: 'value' }]
const checks = []
for (const settings of settingsList) {
  for (const m of matched) checks.push({ columns: m.out, fields: m.fields, settings, issues: T.checkMapping(m.out, m.fields, settings) })
  for (const f of forms) {
    checks.push({ columns: f.columns, fields, settings, issues: T.checkMapping(f.columns, fields, settings) })
    checks.push({ columns: f.messed, fields, settings, issues: T.checkMapping(f.messed, fields, settings) })
    const dup = [...f.columns, { ...f.columns[6], column: 'dup' }, { column: 'need', type: 'INT', source: null, nullable: false, existing: true }]
    checks.push({ columns: dup, fields, settings, issues: T.checkMapping(dup, fields, settings) })
    const typesSwap = f.columns.map((c, i) => ({ ...c, type: ['BOOLEAN', 'JSON', 'INT', 'DATE', 'TEXT', 'BLOB', 'NUMBER(1)', 'BIT', 'TIMESTAMP', 'MONEY'][i % 10] }))
    checks.push({ columns: typesSwap, fields, settings, issues: T.checkMapping(typesSwap, fields, settings) })
  }
}
const values = [null, '', 'a', 'z', '3', 3, 0, 2.5, '12.5', 'abc', true, false, 'true', 'yes', 'no', ['a', 'b'], ['b', 'zz'], [], [3, null],
  { first: 'Ana', last: 'Silva', title: 'Dr' }, { line1: '1 Main', city: 'Leeds', postal_code: 'LS1', country: 'GB' }, { from: '2026-01-01', to: '2026-01-05' },
  { hours: '2', minutes: 5 }, { r1: 'a', r2: 'b', r3: 3 }, [{ id: 'f1', name: 'cv.pdf' }, 'loose.txt'], '2026-10-11', '13:45', 1e21, -0.5, 'Infinity', ' 7 ', [5]]
const facts = { id: '0192a3b4-0000-7000-8000-000000000001', submitted_at: '2026-10-11T08:00:00.000Z', form_version: 3, language: 'fr', number: 42, email: null, review_status: 'new' }
const rows = []
for (const f of forms) {
  if (f.engine !== 'postgresql' && f.engine !== 'oracle') continue
  const all = [...f.columns, ...f.extra.filter(c => c.source?.kind === 'meta'), { column: 'loose', type: 'TEXT', source: null, nullable: true, existing: true }, { column: 'gone', type: 'TEXT', source: { kind: 'field', key: 'gone' }, nullable: true, existing: true }]
  values.forEach((value, i) => {
    const answers = Object.fromEntries([...fields.map(fl => [fl.key, value]), ['gone', value]])
    for (const choices of ['value', 'label']) {
      rows.push({ columns: all, answers, choices, multi: f.multi, facts: i % 2 ? facts : { ...facts, form_version: null, email: 'ana@example.com' }, row: T.rowFor(all, [...fields, ...plain], answers, i % 2 ? facts : { ...facts, form_version: null, email: 'ana@example.com' }, { multi_value: f.multi, choices }, v => Array.isArray(v) ? v.map(x => String(x?.id ?? x)) : [String(v)]) })
    }
  })
}
const dbTypes = ['BOOLEAN', 'BIT', 'TINYINT(1)', 'NUMBER(1)', 'JSON', 'JSONB', 'INT', 'BIGINT', 'INTEGER', 'SERIAL', 'NUMBER(10)', 'NUMBER(19)', 'NUMBER', 'NUMERIC(18,4)', 'FLOAT', 'MONEY',
  'TIMESTAMP', 'TIMESTAMPTZ', 'DATETIME(3)', 'DATE', 'TIME', 'TIME(3)', 'VARCHAR(200)', 'VARCHAR2(1000 CHAR)', 'NVARCHAR(MAX)', 'CHAR(36)', 'text', 'smallint', 'UNIQUEIDENTIFIER']
const kinds = dbTypes.map(type => ({ type, kind: V.kindOfType(type), length: V.lengthOf(type) }))
process.stdout.write(JSON.stringify({ about: 'Recorded from the frontend by scripts/dump_table_rules.py. Do not edit.', names, restChecks, normalised, types, fields, plain, forms, sql, matched, checks, rows, kinds }))
"""


def main() -> None:
    result = run_in_node(ENTRY, {})
    OUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(result['rows'])} rows, {len(result['checks'])} checks")


if __name__ == "__main__":
    main()
