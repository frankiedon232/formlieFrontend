import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { DEFAULT_LOCALE, SITE_LOCALES } from '../app/utils/locales'

const dir = join(import.meta.dirname, '../i18n/locales')

type Messages = { [key: string]: string | Messages }

function keys(messages: Messages, prefix = ''): string[] {
  return Object.entries(messages).flatMap(([key, value]) =>
    typeof value === 'string' ? [`${prefix}${key}`] : keys(value, `${prefix}${key}.`),
  )
}

function strings(messages: Messages): string[] {
  return Object.values(messages).flatMap(value => (typeof value === 'string' ? [value] : strings(value)))
}

const load = (code: string): Messages => JSON.parse(readFileSync(join(dir, `${code}.json`), 'utf8'))

describe('languages (CLAUDE.md rule 4)', () => {
  it('has the same 20 languages as the app, Arabic right to left', () => {
    expect(SITE_LOCALES).toHaveLength(20)
    expect(SITE_LOCALES.filter(locale => locale.dir === 'rtl').map(locale => locale.code)).toEqual(['ar'])
    expect(SITE_LOCALES[0]?.code).toBe(DEFAULT_LOCALE)
  })

  it('has one message file per language and nothing else', () => {
    const files = readdirSync(dir).map(file => file.replace(/\.json$/, ''))
    expect(files.sort()).toEqual(SITE_LOCALES.map(locale => locale.code).sort())
  })

  const english = keys(load(DEFAULT_LOCALE)).sort()

  it.each(SITE_LOCALES.map(locale => locale.code))('%s has every English key', code => {
    expect(keys(load(code)).sort()).toEqual(english)
  })

  it.each(SITE_LOCALES.map(locale => locale.code))('%s has no em dashes (rule 6)', code => {
    expect(strings(load(code)).filter(text => text.includes('—'))).toEqual([])
  })
})
