import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
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

const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map(m => m[1]).sort()
const english = flatten(load('en'))

describe('locales', () => {
  it('has one file per configured language and nothing else', () => {
    const files = readdirSync(dir)
      .map(file => file.replace(/\.json$/, ''))
      .sort()
    expect(files).toEqual(APP_LOCALES.map(locale => locale.code).sort())
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
