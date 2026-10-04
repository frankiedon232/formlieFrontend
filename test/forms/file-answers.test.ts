import { describe, expect, it } from 'vitest'
import { fileAnswers, isFileAnswer, isFileField, MAX_RESPONDENT_FILE_BYTES, maxFileBytes } from '../../shared/utils/forms/file-answers'

describe('file answers', () => {
  const answer = { id: 'abc', name: 'cv.pdf', size: 1200, type: 'application/pdf' }

  it('recognises file questions', () => {
    expect(isFileField('file_upload')).toBe(true)
    expect(isFileField('image_upload')).toBe(true)
    expect(isFileField('signature')).toBe(false)
  })

  it('keeps only real file answers', () => {
    expect(isFileAnswer(answer)).toBe(true)
    expect(isFileAnswer({ name: 'cv.pdf' })).toBe(false)
    expect(fileAnswers([answer, { id: 1 }, 'x'])).toEqual([answer])
    expect(fileAnswers(answer)).toEqual([])
    expect(fileAnswers(null)).toEqual([])
  })

  it('caps the size limit', () => {
    expect(maxFileBytes(undefined)).toBe(10 * 1024 * 1024)
    expect(maxFileBytes({ max_mb: 2 })).toBe(2 * 1024 * 1024)
    expect(maxFileBytes({ max_mb: 500 })).toBe(MAX_RESPONDENT_FILE_BYTES)
    expect(maxFileBytes({ max_mb: 'x' })).toBe(10 * 1024 * 1024)
  })
})
