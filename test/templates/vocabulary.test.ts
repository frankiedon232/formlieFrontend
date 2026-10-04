import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { APP_LOCALES } from '../../shared/utils/i18n/locales'

// Everyday form words (owner, 2026-10-04): every language translates every word.
const dir = join(process.cwd(), 'shared', 'templates', 'vocabulary')
const english = JSON.parse(readFileSync(join(dir, 'en.json'), 'utf8')) as string[]

describe('form vocabulary', () => {
  it('has unique English words', () => {
    expect(new Set(english.map(word => word.toLowerCase())).size).toBe(english.length)
  })

  it.each(APP_LOCALES.map(l => l.code).filter(code => code !== 'en'))('%s translates every word', code => {
    const dict = JSON.parse(readFileSync(join(dir, `${code}.json`), 'utf8')) as Record<string, string>
    const missing = english.filter(word => !dict[word]?.trim())
    expect(missing.slice(0, 5), `${missing.length} missing`).toEqual([])
  })
})
