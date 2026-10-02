import { describe, expect, it } from 'vitest'
import { acceptsFile, normaliseFileType, parseAccept } from '../../shared/utils/forms/file-types'

describe('file types', () => {
  it('normalises what people type', () => {
    expect(normaliseFileType('PDF')).toBe('.pdf')
    expect(normaliseFileType('*.Docx')).toBe('.docx')
    expect(normaliseFileType('image/*')).toBe('image/*')
    expect(normaliseFileType('not a type!')).toBeNull()
    expect(parseAccept('image/*, .pdf,bad type')).toEqual(['image/*', '.pdf'])
  })

  it('checks files against the accept list (empty = anything)', () => {
    const pdf = { name: 'Report.PDF', type: 'application/pdf' }
    const photo = { name: 'a.heic', type: 'image/heic' }
    expect(acceptsFile('', pdf)).toBe(true)
    expect(acceptsFile('.pdf', pdf)).toBe(true)
    expect(acceptsFile('image/*', photo)).toBe(true)
    expect(acceptsFile('image/*', pdf)).toBe(false)
  })
})
