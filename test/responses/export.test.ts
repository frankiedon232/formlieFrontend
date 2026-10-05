import { describe, expect, it } from 'vitest'
import { textPdf } from '../../server/mock/core/pdf'
import { answerText } from '../../shared/utils/forms/answer-text'

// Response exports (F11 M3): answers as plain text for files, and the mock's PDF writer.
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

describe('mock PDF writer', () => {
  it('writes a valid PDF and adds pages when the text is long', () => {
    const short = new TextDecoder('latin1').decode(textPdf('Title', ['# One', 'Line']))
    expect(short.startsWith('%PDF-1.4')).toBe(true)
    expect(short.trimEnd().endsWith('%%EOF')).toBe(true)
    expect(short).toContain('/Count 1')
    const long = new TextDecoder('latin1').decode(textPdf('Title', Array.from({ length: 200 }, (_, i) => `Line ${i}`)))
    expect(Number(/\/Count (\d+)/.exec(long)?.[1])).toBeGreaterThan(1)
  })

  it('escapes brackets and keeps accented Latin letters', () => {
    const text = new TextDecoder('latin1').decode(textPdf('Café (test)', []))
    expect(text).toContain('Café \\(test\\)')
  })
})
