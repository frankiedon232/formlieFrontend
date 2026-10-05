import { describe, expect, it } from 'vitest'
import { parametersIn, splitStatements, statementAt, statementKind, tablesIn } from '#shared/utils/datasources/sql'

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
