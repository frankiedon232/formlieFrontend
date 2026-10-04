import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { formTexts, mainLanguage, translateSchema } from '#shared/utils/forms/translations'

/**
 * Builder: the form's other languages (F10 M4, decision 99). Adding a language fills in every text
 * the built-in dictionaries know (the same ones the main language change uses, no outside
 * service); the creator's own words wait in the translation screen. Every change is one undo step.
 */
export function useFormTranslations() {
  const builder = useBuilder()
  const schema = builder.schema
  const session = injectBuilderSession()
  const api = useApi()

  const main = computed(() => mainLanguage(schema.value))
  const extras = computed(() => (schema.value?.settings?.languages ?? []).filter(code => code !== main.value))
  /** The title respondents see: the form's own title, else its name. */
  const formTitle = computed(() => schema.value?.settings?.title || session?.form.value?.name || '')

  /** Add a language and fill in what the dictionaries know; returns how many texts were filled in. */
  async function add(code: string): Promise<{ filled: number; total: number }> {
    const current = schema.value
    if (!current || code === main.value || extras.value.includes(code)) return { filled: 0, total: 0 }
    builder.history.record()
    current.settings = { ...current.settings, languages: [...extras.value, code] }
    const withTitle = { ...current, settings: { ...current.settings, title: formTitle.value } }
    const { data } = await api.post<{ schema: FormSchemaV1 }>('/templates/translate-content', { schema: withTitle, from: main.value, to: code })
    const source = new Map(formTexts(withTitle).map(item => [item.key, item.text]))
    const filled: Record<string, string> = {}
    for (const item of formTexts(data.schema)) if (source.has(item.key) && item.text !== source.get(item.key)) filled[item.key] = item.text
    if (!schema.value?.settings?.languages?.includes(code)) return { filled: 0, total: 0 }
    schema.value.translations = { ...schema.value.translations, [code]: { ...filled, ...schema.value.translations?.[code] } }
    return { filled: Object.keys(filled).length, total: source.size }
  }

  function remove(code: string) {
    const current = schema.value
    if (!current) return
    builder.history.record()
    current.settings = { ...current.settings, languages: extras.value.filter(item => item !== code) }
    const { [code]: _gone, ...rest } = current.translations ?? {}
    current.translations = rest
  }

  /** One translated text (typing groups into one undo step per text). */
  function set(code: string, key: string, text: string) {
    const current = schema.value
    if (!current) return
    builder.history.record(`translate:${code}:${key}`)
    current.translations = { ...current.translations, [code]: { ...current.translations?.[code], [key]: text } }
  }

  /**
   * The main language becomes one the form already offers (decision 99): its translations become
   * the form's text and the old main text is kept as a translation, so nothing is lost.
   */
  function promote(code: string) {
    const current = schema.value
    if (!current || !extras.value.includes(code)) return
    builder.history.record()
    const old = main.value
    const oldTexts = Object.fromEntries(formTexts(current).map(item => [item.key, item.text]))
    const swapped = translateSchema(current, code)
    const { [code]: _promoted, ...others } = current.translations ?? {}
    current.pages = swapped.pages
    current.thank_you = swapped.thank_you
    if (swapped.theme) current.theme = swapped.theme
    current.settings = { ...swapped.settings, language: code, languages: [...extras.value.filter(item => item !== code), old] }
    current.translations = { ...others, [old]: oldTexts }
  }

  return { main, extras, formTitle, add, remove, set, promote }
}
