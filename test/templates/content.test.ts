import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { allFields } from '../../shared/utils/forms/build'
import { calculateResult } from '../../shared/utils/forms/formula'
import { APP_LOCALES } from '../../shared/utils/i18n/locales'
import { SYSTEM_TEMPLATES, localiseSchema, schemaTexts, systemTemplate, templateSchema } from '../../shared/templates'

const english = [...new Set(SYSTEM_TEMPLATES.flatMap(def => schemaTexts(templateSchema(def))))]
const dictOf = (code: string) => JSON.parse(readFileSync(join(process.cwd(), 'shared', 'templates', 'messages', `${code}.json`), 'utf8')) as Record<string, string>
const tags = (text: string) => (text.match(/<\/?[a-z][^>]*>/gi) ?? []).join('')

describe('template content in every language', () => {
  it('translates text only — keys, values, scores and logic stay the same', () => {
    const schema = templateSchema(systemTemplate('quiz_assessment')!)
    const local = localiseSchema(schema, { Score: 'Punkte', Wind: 'Wind (de)', Pass: 'Bestanden', Questions: 'Fragen' }, 'de')
    expect(local.settings.language).toBe('de')
    expect(local.pages[1]!.title).toBe('Fragen')
    const fields = allFields(local)
    const q1 = fields.find(f => f.key === 'q1')!
    expect(q1.options!.find(o => o.value === 'wind')!.label).toBe('Wind (de)')
    expect(q1.options!.find(o => o.value === 'wind')!.score).toBe(1)
    expect(String(fields.find(f => f.key === 'result')!.props!.formula)).toContain('"Bestanden"')
    expect(local.logic).toEqual(schema.logic)
    // Calculations still work on the translated form.
    const byKey = new Map(fields.map(f => [f.key, f]))
    expect(calculateResult(String(byKey.get('result')!.props!.formula), { percentage: 80 }, byKey)).toBe('Bestanden')
    // Values compared against answers are not text: they stay, so the calculation still works.
    const rsvp = allFields(localiseSchema(templateSchema(systemTemplate('rsvp')!), { yes: 'oui' }, 'fr')).find(f => f.key === 'guests')!
    expect(String(rsvp.props!.formula)).toContain('= "yes"')
    // The original is untouched.
    expect(allFields(schema).find(f => f.key === 'q1')!.options![1]!.label).toBe('Wind')
  })

  it.each(APP_LOCALES.map(l => l.code).filter(code => code !== 'en'))('%s covers every template text', code => {
    const file = join(process.cwd(), 'shared', 'templates', 'messages', `${code}.json`)
    expect(existsSync(file), file).toBe(true)
    const dict = dictOf(code)
    const missing = english.filter(text => !dict[text]?.trim())
    expect(missing.slice(0, 5), `${missing.length} missing`).toEqual([])
    for (const text of english.filter(s => s.includes('<'))) expect(tags(dict[text]!), text).toBe(tags(text))
    for (const text of english) for (const ph of text.match(/\{[a-z_]+\}/g) ?? []) expect(dict[text], text).toContain(ph)
  })
})
