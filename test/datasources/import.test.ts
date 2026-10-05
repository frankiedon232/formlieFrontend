import { describe, expect, it } from 'vitest'
import type { TableStructure } from '../../shared/types/explorer'
import { importRow } from '../../server/mock/data/importRows'
import { parseCsv } from '../../server/mock/core/tabularRead'

const column = (name: string, type: string, nullable = true, extra = {}) => ({
  name,
  type,
  nullable,
  has_default: false,
  primary: false,
  unique: false,
  default: null,
  references: null,
  ...extra,
})
const structure = {
  columns: [
    column('id', 'BIGINT', false, { primary: true, has_default: true }),
    column('full_name', 'VARCHAR(20)', false),
    column('joined_on', 'DATE'),
    column('active', 'BOOLEAN'),
  ],
  primary_key: ['id'],
} as unknown as TableStructure

describe('importing rows', () => {
  const file = parseCsv(
    'Name,Joined,Active\nAda Lovelace,2026-01-04,yes\nLin,45935,no\n,2026-01-01,yes\nA name that is far too long,2026-01-01,yes\nKim,next week,yes',
  )
  const mapping = { id: null, full_name: 'Name', joined_on: 'Joined', active: 'Active' }
  const results = file.rows.map(line => importRow(structure, file.headers, line, mapping))

  it('types each value by its column', () => {
    expect(results[0]).toEqual({
      values: { id: null, full_name: 'Ada Lovelace', joined_on: '2026-01-04', active: true },
    })
    expect(results[1]).toEqual({
      values: { id: null, full_name: 'Lin', joined_on: '2025-10-05', active: false },
    })
  })

  it('reports the first problem of a row', () => {
    expect(results[2]).toEqual({ problem: { column: 'full_name', problem: 'required' } })
    expect(results[3]).toEqual({ problem: { column: 'full_name', problem: 'length' } })
    expect(results[4]).toEqual({ problem: { column: 'joined_on', problem: 'date' } })
  })
})
