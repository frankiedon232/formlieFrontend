import { describe, expect, it } from 'vitest'
import type { FormSchemaV1 } from '../../shared/utils/forms/schema'
import {
  formLanguages,
  formTexts,
  pickLanguage,
  staleKeys,
  textHash,
  translateSchema,
  translationProgress,
} from '../../shared/utils/forms/translations'

// Forms in several languages (decision 99).
const schema = (): FormSchemaV1 => ({
  schema_version: 1,
  settings: { language: 'en', languages: ['fr', 'xx', 'en'], title: 'Feedback' },
  pages: [
    {
      id: 'p1',
      title: 'About you',
      rows: [
        {
          id: 'r1',
          fields: [
            { id: 'f1', key: 'name', type: 'short_text', label: 'Your name', width: 12, required: true, placeholder: '→' } as never,
            { id: 'f4', key: 'site', type: 'url', label: 'Website', width: 12, required: false, placeholder: 'https://' } as never,
            { id: 'f5', key: 'mail', type: 'email', label: 'Email', width: 12, required: false, placeholder: 'name@example.com' } as never,
            {
              id: 'f2',
              key: 'pick',
              type: 'radio',
              label: 'Pick one',
              width: 12,
              required: false,
              options: [{ value: 'yes', label: 'Yes' }, { value: 'no', label: 'No' }],
            } as never,
            { id: 'f3', key: 'result', type: 'calculated', label: 'Result', width: 12, required: false, props: { formula: 'IF({pick} = "yes", "Pass", "Fail")' } } as never,
          ],
        },
      ],
    },
  ],
  thank_you: { title: 'Thank you!', message: 'We got it.' },
  translations: { fr: { 'field.f1.label': 'Votre nom', 'field.f2.option.yes': 'Oui', 'field.f3.formula.0': 'Réussi', 'thanks.title': '  ' } },
})

describe('form translations', () => {
  it('lists every text with a stable key, values and compared text left out', () => {
    const keys = formTexts(schema()).map(item => item.key)
    expect(keys).toEqual([
      'form.title',
      'page.p1.title',
      'field.f1.label',
      'field.f4.label',
      'field.f5.label',
      'field.f2.label',
      'field.f2.option.yes',
      'field.f2.option.no',
      'field.f3.label',
      'field.f3.formula.0',
      'field.f3.formula.1',
      'thanks.title',
      'thanks.message',
    ])
  })

  it('offers the main language first, only known languages, no repeats', () => {
    expect(formLanguages(schema())).toEqual(['en', 'fr'])
    expect(formLanguages(null)).toEqual(['en'])
  })

  it('swaps in translations and keeps the main text where one is missing', () => {
    const fr = translateSchema(schema(), 'fr')
    const field = (id: string) => fr.pages[0]!.rows[0]!.fields.find(item => item.id === id)!
    expect(fr.settings?.language).toBe('fr')
    expect(field('f1').label).toBe('Votre nom')
    expect(field('f2').label).toBe('Pick one')
    expect(field('f2').options).toEqual([{ value: 'yes', label: 'Oui' }, { value: 'no', label: 'No' }])
    expect(field('f3').props?.formula).toBe('IF({pick} = "yes", "Réussi", "Fail")')
    expect(fr.thank_you?.title).toBe('Thank you!')
  })

  it('leaves the form as it is for its main language or one it does not offer', () => {
    const base = schema()
    expect(translateSchema(base, 'en')).toBe(base)
    expect(translateSchema(base, 'de')).toBe(base)
  })

  it('counts what is done', () => {
    expect(translationProgress(schema(), 'fr')).toEqual({ done: 3, total: 13, stale: 0 })
  })

  it('notices when the original changed after translating', () => {
    const form = { ...schema(), translated_from: { fr: { 'field.f1.label': textHash('Your name'), 'field.f2.option.yes': textHash('Yes') } } }
    expect(staleKeys(form, 'fr').size).toBe(0)
    form.pages[0]!.rows[0]!.fields.find(item => item.id === 'f1')!.label = 'Your full name'
    expect([...staleKeys(form, 'fr')]).toEqual(['field.f1.label'])
    expect(translationProgress(form, 'fr').stale).toBe(1)
  })

  it('opens in the main language unless the link asks for another it offers', () => {
    const offered = ['fr', 'en', 'zh-CN']
    expect(pickLanguage(offered, null)).toBe('fr')
    expect(pickLanguage(offered, 'en')).toBe('en')
    expect(pickLanguage(offered, 'de')).toBe('fr')
    expect(pickLanguage([], null)).toBe('en')
  })
})
