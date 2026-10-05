import { describe, expect, it } from 'vitest'
import { jsonExport, quoteName, sqlInsertScript, sqlLiteral } from '#shared/utils/datasources/exportFormats'

const columns = [
  { name: 'id', type: 'BIGINT', primary: true, has_default: true },
  { name: 'full_name', type: 'VARCHAR(200)' },
  { name: 'active', type: 'BOOLEAN' },
  { name: 'joined', type: 'DATE' },
  { name: 'seen_at', type: 'TIMESTAMPTZ' },
  { name: 'meta', type: 'JSONB' },
]
const rows = [
  { id: 1, full_name: "Tom O'Brien", active: true, joined: '2026-08-01', seen_at: '2026-08-01T16:22:23.030Z', meta: '{"a":1}' },
  { id: 2, full_name: null, active: false, joined: null, seen_at: null, meta: null },
]

describe('JSON export', () => {
  it('keeps types and parses JSON columns', () => {
    const list = JSON.parse(jsonExport(columns, rows))
    expect(list[0]).toEqual({ id: 1, full_name: "Tom O'Brien", active: true, joined: '2026-08-01', seen_at: '2026-08-01T16:22:23.030Z', meta: { a: 1 } })
    expect(list[1].full_name).toBeNull()
  })
})

describe('SQL export', () => {
  it('quotes names the engine way', () => {
    expect(quoteName('postgresql', 'a"b')).toBe('"a""b"')
    expect(quoteName('mysql', 'a`b')).toBe('`a``b`')
    expect(quoteName('sqlserver', 'a]b')).toBe('[a]]b]')
  })

  it('writes literals per engine', () => {
    expect(sqlLiteral('postgresql', 'BOOLEAN', true)).toBe('TRUE')
    expect(sqlLiteral('sqlserver', 'BIT', true)).toBe('1')
    expect(sqlLiteral('mysql', 'VARCHAR(20)', "it's a \\ test")).toBe("'it''s a \\\\ test'")
    expect(sqlLiteral('sqlserver', 'NVARCHAR(20)', 'Zoë')).toBe("N'Zoë'")
    expect(sqlLiteral('oracle', 'DATE', '2026-08-01')).toBe("DATE '2026-08-01'")
    expect(sqlLiteral('oracle', 'TIMESTAMP', '2026-08-01T16:22:23.030Z')).toBe("TIMESTAMP '2026-08-01 16:22:23.030'")
    expect(sqlLiteral('mysql', 'DATETIME', '2026-08-01T16:22:23Z')).toBe("'2026-08-01 16:22:23'")
    expect(sqlLiteral('postgresql', 'INTEGER', null)).toBe('NULL')
  })

  it('builds a transaction with one INSERT per row', () => {
    const script = sqlInsertScript('postgresql', { schema: 'public', table: 'clients' }, columns, rows, new Date('2026-10-05T00:00:00Z'))
    expect(script).toContain('BEGIN;')
    expect(script).toContain(`INSERT INTO "public"."clients" ("id", "full_name", "active", "joined", "seen_at", "meta") VALUES (1, 'Tom O''Brien', TRUE, '2026-08-01', '2026-08-01 16:22:23.030', '{"a":1}');`)
    expect(script).toContain('VALUES (2, NULL, FALSE, NULL, NULL, NULL);')
    expect(script.trim().endsWith('COMMIT;')).toBe(true)
  })

  it('switches identity insert on for SQL Server and has no BEGIN on Oracle', () => {
    const sqlServer = sqlInsertScript('sqlserver', { schema: 'dbo', table: 'clients' }, columns, rows)
    expect(sqlServer).toContain('SET IDENTITY_INSERT [dbo].[clients] ON;')
    expect(sqlServer).toContain('SET IDENTITY_INSERT [dbo].[clients] OFF;')
    const oracle = sqlInsertScript('oracle', { schema: 'APP', table: 'CLIENTS' }, columns, rows)
    expect(oracle).not.toContain('BEGIN')
    expect(oracle).toContain('COMMIT;')
  })
})
