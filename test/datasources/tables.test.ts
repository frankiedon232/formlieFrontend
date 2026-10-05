import { describe, expect, it } from 'vitest'
import type { DestinationSettings, TableColumn } from '../../shared/types/destinations'
import { addColumnSql, blocking, checkMapping, columnNameFor, columnsForForm, createTableSql, matchColumns, rowFor, snake, standardSettings, tableNameFor, viewSql } from '../../shared/utils/datasources/tables'

const settings: DestinationSettings = { write_mode: 'insert', key_column: 'response_id', multi_value: 'json', choices: 'value' }
const fields = [
  { key: 'full_name', label: 'Full name', type: 'full_name' },
  { key: 'email', label: 'Email', type: 'email' },
  { key: 'order', label: 'Order', type: 'number' },
  { key: 'start_date', label: 'Start date', type: 'date' },
  { key: 'skills', label: 'Skills', type: 'checkbox', options: [{ value: 'sql', label: 'SQL' }, { value: 'vue', label: 'Vue' }] },
  { key: 'agree', label: 'I agree', type: 'consent' },
  { key: 'cv', label: 'CV', type: 'file_upload' },
] as never[]

describe('response tables', () => {
  it('names tables and columns safely per engine', () => {
    expect(snake('Employee Onboarding (2026)')).toBe('employee_onboarding_2026')
    expect(snake('Café crème')).toBe('cafe_creme')
    expect(snake('3rd party')).toBe('c_3rd_party')
    expect(tableNameFor('postgresql', 'formalie_', 'Job application')).toBe('formalie_job_application')
    expect(tableNameFor('oracle', 'fmly_', 'Job application')).toBe('FMLY_JOB_APPLICATION')
    expect(tableNameFor('postgresql', 'formalie_', 'x'.repeat(100))).toHaveLength(63)
    const taken = new Set<string>()
    expect(columnNameFor('mysql', 'order', taken)).toBe('order_value')
    expect(columnNameFor('mysql', 'email', taken)).toBe('email')
    expect(columnNameFor('mysql', 'Email', taken)).toBe('email_2')
  })

  it('builds columns with each engine’s types and a CREATE TABLE', () => {
    const pg = columnsForForm('postgresql', fields, settings)
    expect(pg.map(column => column.column)).toEqual(['response_id', 'submitted_at', 'form_version', 'language', 'full_name', 'email', 'order_value', 'start_date', 'skills', 'agree', 'cv'])
    expect(pg.find(column => column.column === 'skills')!.type).toBe('JSONB')
    expect(pg.find(column => column.column === 'agree')!.type).toBe('BOOLEAN')
    expect(columnsForForm('sqlserver', fields, settings).find(column => column.column === 'submitted_at')!.type).toBe('DATETIMEOFFSET')
    expect(columnsForForm('oracle', fields, { multi_value: 'text' }).find(column => column.column === 'SKILLS')!.type).toBe('CLOB')
    const sql = createTableSql('postgresql', 'formalie', 'formalie_job_application', pg)
    expect(sql).toContain('CREATE TABLE "formalie"."formalie_job_application" (')
    expect(sql).toContain('"response_id" UUID NOT NULL')
    expect(sql).toContain('PRIMARY KEY ("response_id")')
    expect(createTableSql('sqlserver', 'formalie', 't', pg.slice(0, 2))).toContain('CREATE TABLE [formalie].[t]')
    expect(addColumnSql('oracle', 'APP', 'T', { column: 'NOTE', type: 'CLOB' })).toBe('ALTER TABLE "APP"."T" ADD ("NOTE" CLOB);')
    expect(addColumnSql('postgresql', 'public', 't', { column: 'note', type: 'TEXT' })).toBe('ALTER TABLE "public"."t" ADD COLUMN "note" TEXT;')
  })

  it('matches an existing table and checks the match', () => {
    const column = (name: string, type: string, nullable = true): TableColumn => ({ name, type, nullable, has_default: false, primary: false, unique: false })
    const table = [column('submission_id', 'VARCHAR(64)', false), column('FullName', 'VARCHAR(200)'), column('email', 'VARCHAR(320)'), column('created_at', 'DATETIME'), column('company', 'VARCHAR(200)', false), column('start_date', 'INT')]
    const mapped = matchColumns(table, fields)
    expect(mapped.find(item => item.column === 'submission_id')!.source).toEqual({ kind: 'meta', key: 'response_id' })
    expect(mapped.find(item => item.column === 'FullName')!.source).toEqual({ kind: 'field', key: 'full_name' })
    expect(mapped.find(item => item.column === 'created_at')!.source).toEqual({ kind: 'meta', key: 'submitted_at' })
    const issues = checkMapping(mapped, fields, settings)
    expect(issues).toContainEqual({ code: 'required_unmapped', column: 'company' })
    expect(issues).toContainEqual({ code: 'type_mismatch', column: 'start_date', field: 'start_date' })
    expect(blocking(issues).map(issue => issue.code)).toEqual(['required_unmapped'])
    expect(checkMapping(mapped.filter(item => item.column !== 'submission_id'), fields, settings)).toContainEqual({ code: 'no_key', column: null })
  })

  it('writes a response as a row', () => {
    const columns = columnsForForm('postgresql', fields, settings)
    const facts = { id: 'r1', submitted_at: '2026-10-05T10:00:00Z', form_version: 3, language: 'en', number: 7, email: null, review_status: 'new' }
    const answers = { full_name: { first: 'Ada', last: 'Lovelace' }, email: 'ada@example.com', order: '12', skills: ['sql', 'vue'], agree: true, cv: [{ name: 'cv.pdf' }] }
    const row = rowFor(columns, fields, answers, facts, { multi_value: 'json', choices: 'label' }, () => ['https://files.example/cv.pdf'])
    expect(row).toMatchObject({ response_id: 'r1', form_version: 3, order_value: 12, skills: '["SQL","Vue"]', agree: true, cv: '["https://files.example/cv.pdf"]', start_date: null })
    expect(JSON.parse(row.full_name as string)).toEqual({ first: 'Ada', last: 'Lovelace' })
    expect(rowFor(columns, fields, answers, facts, { multi_value: 'text', choices: 'label' }).skills).toBe('SQL; Vue')
  })

  it('writes Formalie’s own tables one row per response, by its id', () => {
    const columns = columnsForForm('oracle', fields, settings)
    expect(standardSettings({ ...settings, write_mode: 'insert', key_column: 'x' }, columns)).toMatchObject({ write_mode: 'upsert', key_column: 'RESPONSE_ID' })
  })

  it('offers a view named after the questions', () => {
    const columns = columnsForForm('postgresql', fields, settings)
    const sql = viewSql('postgresql', 'public', 'formalie_jobs', columns, new Map([['email', 'Email'], ['order', 'Order "no"']]))
    expect(sql).toContain('CREATE OR REPLACE VIEW "public"."formalie_jobs_view" AS')
    expect(sql).toContain('"email" AS "Email"')
    expect(sql).toContain('"order_value" AS "Order no"')
    expect(sql).toContain('FROM "public"."formalie_jobs";')
    expect(viewSql('sqlserver', 'formalie', 't', columns.slice(0, 1), new Map())).toContain('CREATE OR ALTER VIEW [formalie].[t_view]')
  })
})
