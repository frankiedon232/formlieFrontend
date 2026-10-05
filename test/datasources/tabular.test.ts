import { describe, expect, it } from 'vitest'
import { excelDate, parseCsv, parseXlsx } from '../../server/mock/core/tabularRead'
import { xlsx } from '../../server/mock/core/xlsx'

describe('reading import files', () => {
  it('reads CSV with quotes, semicolons and a byte-order mark', () => {
    expect(parseCsv('﻿name,note\r\nAda,"says ""hi"", twice"\r\n\r\nLin,"two\nlines"\n')).toEqual({
      headers: ['name', 'note'],
      rows: [
        ['Ada', 'says "hi", twice'],
        ['Lin', 'two\nlines'],
      ],
    })
    expect(parseCsv('a;b\n1;2')).toEqual({ headers: ['a', 'b'], rows: [['1', '2']] })
  })

  it('reads the .xlsx files Formalie writes (round trip)', () => {
    const file = xlsx('Sheet', [
      ['name', 'amount', 'note'],
      ['Ada & Co', '12.5', '<b>'],
      ['Lin', '', 'x'],
    ])
    expect(parseXlsx(Buffer.from(file))).toEqual({
      headers: ['name', 'amount', 'note'],
      rows: [
        ['Ada & Co', '12.5', '<b>'],
        ['Lin', '', 'x'],
      ],
    })
    expect(excelDate(45935).slice(0, 10)).toBe('2025-10-05')
  })
})
