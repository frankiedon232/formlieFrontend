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

describe('files a device sends without a type', () => {
  it('match a family by their extension', async () => {
    const { acceptsFile, looksLikePicture } = await import('../../shared/utils/forms/file-types')
    expect(acceptsFile('image/*', { name: 'IMG_0001.HEIC', type: '' })).toBe(true)
    expect(acceptsFile('video/*', { name: 'clip.mkv', type: 'application/octet-stream' })).toBe(true)
    expect(acceptsFile('image/*', { name: 'cv.pdf', type: '' })).toBe(false)
    expect(looksLikePicture({ name: 'IMG_0001.heic', type: '' })).toBe(true)
    expect(looksLikePicture({ name: 'logo.svg', type: 'image/svg+xml' })).toBe(false)
    expect(looksLikePicture({ name: 'cv.pdf', type: 'application/pdf' })).toBe(false)
  })
})
