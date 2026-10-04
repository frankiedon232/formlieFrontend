import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

// Owner, 2026-10-04: no em dash (or spaced en dash) in any text people read. Number ranges (3–60) are fine.
const EM = String.fromCharCode(0x2014)
const EN = String.fromCharCode(0x2013)
const DASH = new RegExp(`${EM}|\\s${EN}\\s`)
const strings = (value: unknown): string[] =>
  typeof value === 'string' ? [value] : value && typeof value === 'object' ? Object.entries(value).flatMap(([key, item]) => [key, ...strings(item)]) : []
const files = (dir: string) => readdirSync(dir).filter(file => file.endsWith('.json')).map(file => join(dir, file))
const root = join(__dirname, '../..')

describe('no dashes in text people read', () => {
  it.each([...files(join(root, 'i18n/locales')), ...files(join(root, 'shared/templates/messages')), ...files(join(root, 'shared/templates/vocabulary'))])('%s', file => {
    const found = strings(JSON.parse(readFileSync(file, 'utf8'))).filter(text => DASH.test(text))
    expect(found.slice(0, 5), `${found.length} with a dash`).toEqual([])
  })
})
