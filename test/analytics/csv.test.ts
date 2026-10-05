import { describe, expect, it } from 'vitest'
import { analyticsCsv } from '../../app/utils/analytics/csv'

describe('analytics CSV', () => {
  it('starts with a BOM, keeps numbers and quotes text that needs it', () => {
    const csv = analyticsCsv([
      ['Form', 'Views'],
      ['Survey, 2026', 120],
      ['Say "hi"', 0],
      [null, 3.5],
    ])
    expect(csv).toBe('\uFEFFForm,Views\r\n"Survey, 2026",120\r\n"Say ""hi""",0\r\n,3.5\r\n')
  })

  it('never lets a spreadsheet run a cell as a formula', () => {
    expect(analyticsCsv([['=SUM(A1)', '+1', '-2', '@x']])).toBe("\uFEFF'=SUM(A1),'+1,'-2,'@x\r\n")
  })
})
