import { describe, expect, it } from 'vitest'
import { kindOfType, lengthOf, parseValue } from '../../shared/utils/datasources/values'

const col = (type: string, nullable = true, has_default = false) => ({ type, nullable, has_default })

describe('column values', () => {
  it('knows the kind of each engine’s types', () => {
    expect(['BIGINT', 'INT', 'INTEGER', 'NUMBER(10)', 'NUMBER(19)'].map(kindOfType)).toEqual([
      'integer',
      'integer',
      'integer',
      'integer',
      'integer',
    ])
    expect(['DECIMAL(12,2)', 'NUMERIC(18,4)', 'NUMBER(12,2)'].map(kindOfType)).toEqual([
      'decimal',
      'decimal',
      'decimal',
    ])
    expect(['BOOLEAN', 'BIT', 'TINYINT(1)', 'NUMBER(1)'].map(kindOfType)).toEqual([
      'boolean',
      'boolean',
      'boolean',
      'boolean',
    ])
    expect(['DATE', 'TIMESTAMPTZ', 'DATETIME2', 'TIME', 'JSONB', 'VARCHAR2(200)'].map(kindOfType)).toEqual([
      'date',
      'datetime',
      'datetime',
      'time',
      'json',
      'text',
    ])
    expect(lengthOf('NVARCHAR(320)')).toBe(320)
    expect(lengthOf('VARCHAR2(35 CHAR)')).toBe(35)
    expect(lengthOf('TEXT')).toBeNull()
  })

  it('turns text into values and says what is wrong', () => {
    expect(parseValue(col('INT'), ' 42 ')).toEqual({ value: 42 })
    expect(parseValue(col('INT'), '4.2')).toEqual({ problem: 'integer' })
    expect(parseValue(col('DECIMAL(12,2)'), '1 250.5')).toEqual({ value: 1250.5 })
    expect(parseValue(col('BOOLEAN'), 'Yes')).toEqual({ value: true })
    expect(parseValue(col('BIT'), 'maybe')).toEqual({ problem: 'boolean' })
    expect(parseValue(col('DATE'), '2026-10-05')).toEqual({ value: '2026-10-05' })
    expect(parseValue(col('DATE'), '05/10/2026')).toEqual({ problem: 'date' })
    expect(parseValue(col('JSONB'), '{"a":1}')).toEqual({ value: '{"a":1}' })
    expect(parseValue(col('JSONB'), '{a:1}')).toEqual({ problem: 'json' })
    expect(parseValue(col('VARCHAR(3)'), 'abcd')).toEqual({ problem: 'length' })
    expect(parseValue(col('VARCHAR(3)', false), '')).toEqual({ problem: 'required' })
    expect(parseValue(col('BIGINT', false, true), '')).toEqual({ value: null })
    expect(parseValue(col('VARCHAR(3)'), '')).toEqual({ value: null })
  })
})
