import { describe, expect, it } from 'vitest'
import { formatSql, parametersIn, scriptKind, splitStatements, statementAt, statementKind, tablesIn } from '#shared/utils/datasources/sql'

describe('statements', () => {
  it('splits on semicolons outside quotes, comments and dollar quotes', () => {
    const sql = "SELECT 'a;b' FROM t; -- one; two\nUPDATE t SET x = 1;\n/* ; */ SELECT $$;$$"
    expect(splitStatements(sql).map(item => item.text)).toEqual(["SELECT 'a;b' FROM t", '-- one; two\nUPDATE t SET x = 1', '/* ; */ SELECT $$;$$'])
  })

  it('finds the statement at the cursor', () => {
    const sql = 'SELECT 1;\nSELECT 2;\n\nSELECT 3'
    expect(statementAt(sql, 0)?.text).toBe('SELECT 1')
    expect(statementAt(sql, 12)?.text).toBe('SELECT 2')
    expect(statementAt(sql, sql.length)?.text).toBe('SELECT 3')
  })

  it('ignores empty statements and comment-only ones', () => {
    expect(splitStatements(';; -- nothing\n;')).toEqual([])
  })
})

describe('kinds', () => {
  it('tells reads, changes and structure apart', () => {
    expect(statementKind('select * from t')).toBe('read')
    expect(statementKind('WITH x AS (SELECT 1) SELECT * FROM x')).toBe('read')
    expect(statementKind('WITH gone AS (DELETE FROM t RETURNING *) SELECT * FROM gone')).toBe('delete')
    expect(statementKind("UPDATE t SET note = 'delete me'")).toBe('update')
    expect(statementKind('INSERT INTO t VALUES (1)')).toBe('insert')
    expect(statementKind('SELECT * INTO copy FROM t')).toBe('insert')
    expect(statementKind('-- note\nDROP TABLE t')).toBe('structure')
    expect(statementKind('TRUNCATE t')).toBe('structure')
    expect(statementKind('VACUUM')).toBe('other')
  })

  it('gives a script the kind of its strongest statement', () => {
    expect(scriptKind('SELECT client_id, title FROM intake.cases;\n\nSELECT * FROM intake.cases;')).toBe('read')
    expect(scriptKind('SELECT 1; DELETE FROM t WHERE id = 1; UPDATE t SET a = 1')).toBe('delete')
  })
})

describe('tables and parameters', () => {
  it('lists the tables a statement names', () => {
    expect(tablesIn('SELECT * FROM public.clients c JOIN "intake"."cases" k ON k.client_id = c.id')).toEqual(['public.clients', 'intake.cases'])
    expect(tablesIn('UPDATE [dbo].[orders] SET total = 0')).toEqual(['dbo.orders'])
  })

  it('finds :name parameters, never casts or quoted text', () => {
    expect(parametersIn("SELECT * FROM t WHERE a = :status AND b::text = ':nope' AND c > :since AND d = :status")).toEqual(['status', 'since'])
  })
})

describe('format', () => {
  it('puts clauses on their own lines and indents lists and conditions', () => {
    expect(formatSql("select id, full_name from public.clients where status = 'open' and phone is null order by id desc limit 10")).toBe(
      ["SELECT", "  id,", "  full_name", "FROM public.clients", "WHERE status = 'open'", "  AND phone IS NULL", "ORDER BY", "  id DESC", "LIMIT 10;"].join('\n'),
    )
  })

  it('keeps strings, quoted names and functions as they are', () => {
    expect(formatSql(`select count(*) from "My Table" where note = 'select from where'`)).toBe(['SELECT', '  COUNT(*)', 'FROM "My Table"', "WHERE note = 'select from where';"].join('\n'))
  })

  it('formats changes and several statements', () => {
    expect(formatSql("update t set a = 1, b = 'x' where id in (1, 2); delete from t where id = 3")).toBe(
      ['UPDATE t', 'SET', '  a = 1,', "  b = 'x'", 'WHERE id IN (1, 2);', '', 'DELETE FROM t', 'WHERE id = 3;'].join('\n'),
    )
  })
})
