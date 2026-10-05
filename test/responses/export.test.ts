import { describe, expect, it } from 'vitest'
import { answerText } from '../../shared/utils/forms/answer-text'

// Response exports (F11 M3): answers as plain text for files, the Excel writer and the PDF report.
describe('answers in export files', () => {
  const choice = { type: 'checkbox', options: [{ value: 'a', label: 'Apples' }, { value: 'b', label: 'Bananas' }] } as never

  it('uses option labels and joins several picks', () => {
    expect(answerText(choice, ['a', 'b'])).toBe('Apples; Bananas')
    expect(answerText({ type: 'radio', options: [{ value: 'x', label: 'Remote' }] } as never, 'x')).toBe('Remote')
  })

  it('keeps stable values for dates, names, addresses and files', () => {
    expect(answerText({ type: 'date_range' } as never, { from: '2026-01-02', to: '2026-01-09' })).toBe('2026-01-02 / 2026-01-09')
    expect(answerText({ type: 'full_name' } as never, { first: 'Ada', last: 'Okafor' })).toBe('Ada Okafor')
    expect(answerText({ type: 'address' } as never, { line1: '1 Main St', city: 'Springfield', country: 'GB' })).toBe('1 Main St, Springfield, GB')
    expect(answerText({ type: 'file_upload' } as never, [{ name: 'cv.pdf' }, { name: 'id.png' }])).toBe('cv.pdf; id.png')
  })

  it('words yes / no in the caller language and leaves empty answers empty', () => {
    expect(answerText({ type: 'toggle' } as never, true, { yes: 'Ja', no: 'Nein', agreed: 'OK' })).toBe('Ja')
    expect(answerText({ type: 'toggle' } as never, false)).toBe('No')
    expect(answerText({ type: 'short_text' } as never, '')).toBe('')
    expect(answerText({ type: 'rich_text' } as never, '<p>Hello <b>there</b></p>')).toBe('Hello there')
  })
})

describe('mock Excel writer', () => {
  it('writes a ZIP workbook with the sheet, header style and every cell', async () => {
    const { xlsx } = await import('../../server/mock/core/xlsx')
    const bytes = xlsx('Job application: 2024/1', [
      ['Number', 'Name', 'Answer'],
      [1, 'Ada Okafor', 'Café & <tea>'],
      [2, 'Jean Dupont', '=1+1'],
    ])
    const text = new TextDecoder('latin1').decode(bytes)
    expect(text.startsWith('PK\u0003\u0004')).toBe(true)
    for (const name of ['[Content_Types].xml', 'xl/workbook.xml', 'xl/worksheets/sheet1.xml', 'xl/styles.xml']) expect(text).toContain(name)
    const sheet = new TextDecoder().decode(bytes)
    expect(sheet).toContain('<v>1</v>')
    expect(sheet).toContain('Café &amp; &lt;tea&gt;')
    // Text that looks like a formula stays text (inline string), never a formula.
    expect(sheet).toContain('<t xml:space="preserve">=1+1</t>')
    expect(sheet).not.toContain('<f>')
    expect(sheet).toContain('name="Job application  2024 1"')
    if (process.env.XLSX_OUT) (await import('node:fs')).writeFileSync(process.env.XLSX_OUT, bytes)
  })
})

describe('response report PDF', () => {
  it('lays out a cover, status tiles and one card per response over several pages', async () => {
    const { responseReport } = await import('../../server/mock/data/responseReport')
    const responses = Array.from({ length: 9 }, (_, i) => ({
      number: 1936 - i,
      name: ['Arjun Johansson', 'Selin Haddad', 'Liam Kowalski'][i % 3]!,
      email: `person${i}@example.org`,
      submitted: '2026-10-05 09:30 UTC',
      status: (['new', 'reviewed', 'approved', 'rejected'] as const)[i % 4]!,
      channel: i % 2 ? 'embed' : 'link',
      tags: i % 3 ? [] : ['priority'],
      answers: [
        { question: 'Full name', answer: 'Arjun Johansson' },
        { question: 'Email', answer: 'arjun@example.org' },
        { question: 'Why do you want to join our team? Tell us in a few sentences.', answer: 'I enjoy building tools that help people work better together, and your mission matches what I care about. '.repeat(3) },
        { question: 'Country of residence', answer: '' },
        { question: 'Work arrangement', answer: 'Remote' },
      ],
    }))
    const bytes = responseReport({ org: 'Remedy Legal', form: 'Job application 2', brand: '#2f6f5e', exportedBy: 'Frankie Don', exportedAt: new Date('2026-10-05T10:00:00Z'), scope: 'All responses', counts: { new: 3, reviewed: 2, approved: 2, rejected: 2 }, responses })
    const text = new TextDecoder('latin1').decode(bytes)
    expect(text.startsWith('%PDF-1.4')).toBe(true)
    expect(Number(/\/Count (\d+)/.exec(text)?.[1])).toBeGreaterThan(1)
    expect(text).toContain('(Page 1 of ')
    expect(text).toContain('(Job application 2)')
    if (process.env.PDF_OUT) (await import('node:fs')).writeFileSync(process.env.PDF_OUT, bytes)
  })
})
