import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { ERROR_CODES } from '../../shared/utils/errors/codes'
import { APP_LOCALES } from '../../shared/utils/i18n/locales'

// CLAUDE.md rule 17: every string exists in every language, with the same {placeholders}.
type Messages = { [key: string]: string | Messages }

const dir = join(__dirname, '../../i18n/locales')
const load = (code: string) => JSON.parse(readFileSync(join(dir, `${code}.json`), 'utf8')) as Messages

function flatten(messages: Messages, prefix = ''): Record<string, string> {
  return Object.entries(messages).reduce<Record<string, string>>((acc, [key, value]) => {
    if (typeof value === 'string') acc[prefix + key] = value
    else Object.assign(acc, flatten(value, `${prefix}${key}.`))
    return acc
  }, {})
}

// vue-i18n syntax: a bare @ starts a linked message and | splits plurals, escape @ as {'@'}.
const unescapedAt = (text: string) => /@/.test(text.replace(/{'@'}/g, ''))
const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map(m => m[1]).sort()
const english = flatten(load('en'))

describe('locales', () => {
  // vue-i18n reads <word> as HTML and refuses the whole file (dev server error, 2026-10-06)
  it('has no HTML-like <tags> in any message', () => {
    for (const { code } of APP_LOCALES) {
      const tagged = Object.entries(flatten(load(code))).filter(([, text]) => /<[^>]*>/.test(text)).map(([key]) => key)
      expect(tagged, code).toEqual([])
    }
  })

  it('translates every FRM-* error code (server catalogue + client network codes)', () => {
    const codes = [...Object.keys(ERROR_CODES), 'FRM-NET-1000', 'FRM-NET-1001', 'FRM-NET-1002']
    for (const code of codes) expect(english[`errors.${code}`], code).toBeTruthy()
  })

  it('has one file per configured language and nothing else', () => {
    const files = readdirSync(dir)
      .map(file => file.replace(/\.json$/, ''))
      .sort()
    expect(files).toEqual(APP_LOCALES.map(locale => locale.code).sort())
  })

  it.each(APP_LOCALES.map(locale => locale.code))('%s has no unescaped @ (vue-i18n linked syntax)', code => {
    for (const [key, value] of Object.entries(flatten(load(code))))
      expect(unescapedAt(value), key).toBe(false)
  })

  it.each(APP_LOCALES.filter(locale => locale.code !== 'en').map(locale => locale.code))(
    '%s has every English key, no extras, same placeholders, no empty strings',
    code => {
      const messages = flatten(load(code))
      expect(Object.keys(messages).sort()).toEqual(Object.keys(english).sort())
      for (const [key, value] of Object.entries(messages)) {
        expect(value.trim(), key).not.toBe('')
        expect(placeholders(value), key).toEqual(placeholders(english[key]!))
      }
    },
  )
})
