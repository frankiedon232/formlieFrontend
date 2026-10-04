import { describe, expect, it } from 'vitest'
import type { FormSchemaV1 } from '../../shared/utils/forms/schema'
import {
  acceptedLanguages,
  formLanguages,
  formTexts,
  pickLanguage,
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
    const fields = fr.pages[0]!.rows[0]!.fields
    expect(fr.settings?.language).toBe('fr')
    expect(fields[0]!.label).toBe('Votre nom')
    expect(fields[1]!.label).toBe('Pick one')
    expect(fields[1]!.options).toEqual([{ value: 'yes', label: 'Oui' }, { value: 'no', label: 'No' }])
    expect(fields[2]!.props?.formula).toBe('IF({pick} = "yes", "Réussi", "Fail")')
    expect(fr.thank_you?.title).toBe('Thank you!')
  })

  it('leaves the form as it is for its main language or one it does not offer', () => {
    const base = schema()
    expect(translateSchema(base, 'en')).toBe(base)
    expect(translateSchema(base, 'de')).toBe(base)
  })

  it('counts what is done', () => {
    expect(translationProgress(schema(), 'fr')).toEqual({ done: 3, total: 11 })
  })

  it('picks the link language, then the browser language, then the main one', () => {
    const offered = ['en', 'fr', 'zh-CN']
    expect(pickLanguage(offered, 'fr', ['zh-CN'])).toBe('fr')
    expect(pickLanguage(offered, 'de', ['fr-CA', 'en'])).toBe('fr')
    expect(pickLanguage(offered, null, ['zh-cn'])).toBe('zh-CN')
    expect(pickLanguage(offered, null, ['de'])).toBe('en')
    expect(acceptedLanguages('de;q=0.5, fr-CA, en;q=0.8, *')).toEqual(['fr-CA', 'en', 'de'])
  })
})
