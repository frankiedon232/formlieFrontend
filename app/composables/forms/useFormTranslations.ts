import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { formTexts, mainLanguage, textHash, translateSchema } from '#shared/utils/forms/translations'

/**
 * Builder: the form's other languages (F10 M4, decision 99). Adding a language fills in every text
 * the built-in dictionaries know (the same ones the main language change uses, no outside
 * service); the creator's own words wait in the translation screen. Every change is one undo step.
 * Each translation remembers a fingerprint of the text it was made from, so a later change to the
 * original shows "check the translation".
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
    // Fill in first, then change the form: a failed fill leaves the form exactly as it was.
    const withTitle = { ...current, settings: { ...current.settings, title: formTitle.value } }
    const { data } = await api.post<{ schema: FormSchemaV1 }>('/templates/translate-content', { schema: withTitle, from: main.value, to: code })
    const source = new Map(formTexts(withTitle).map(item => [item.key, item.text]))
    const filled: Record<string, string> = {}
    for (const item of formTexts(data.schema)) if (source.has(item.key) && item.text !== source.get(item.key)) filled[item.key] = item.text
    if (!schema.value || extras.value.includes(code) || code === main.value) return { filled: 0, total: 0 }
    builder.history.record()
    schema.value.settings = { ...schema.value.settings, languages: [...extras.value, code] }
    schema.value.translations = { ...schema.value.translations, [code]: { ...filled, ...schema.value.translations?.[code] } }
    const hashes = Object.fromEntries(Object.keys(filled).map(key => [key, textHash(source.get(key) ?? '')]))
    schema.value.translated_from = { ...schema.value.translated_from, [code]: { ...hashes, ...schema.value.translated_from?.[code] } }
    return { filled: Object.keys(filled).length, total: source.size }
  }

  function remove(code: string) {
    const current = schema.value
    if (!current) return
    builder.history.record()
    current.settings = { ...current.settings, languages: extras.value.filter(item => item !== code) }
    const { [code]: _gone, ...rest } = current.translations ?? {}
    current.translations = rest
    const { [code]: _from, ...restFrom } = current.translated_from ?? {}
    current.translated_from = restFrom
  }

  /** One translated text, made from `source` (typing groups into one undo step per text). */
  function set(code: string, key: string, text: string, source: string) {
    const current = schema.value
    if (!current) return
    builder.history.record(`translate:${code}:${key}`)
    current.translations = { ...current.translations, [code]: { ...current.translations?.[code], [key]: text } }
    current.translated_from = { ...current.translated_from, [code]: { ...current.translated_from?.[code], [key]: textHash(source) } }
  }

  /** "Still right": the translation is checked against the changed original. */
  function confirm(code: string, key: string, source: string) {
    const current = schema.value
    if (!current) return
    builder.history.record()
    current.translated_from = { ...current.translated_from, [code]: { ...current.translated_from?.[code], [key]: textHash(source) } }
  }

  /**
   * The main text moved to another language (language change): translations that matched the old
   * text match the new one, so other languages don't all turn into "check the translation".
   */
  function rebase(before: Map<string, string>) {
    const current = schema.value
    if (!current?.translated_from) return
    const after = new Map(formTexts(current).map(item => [item.key, textHash(item.text)]))
    current.translated_from = Object.fromEntries(
      Object.entries(current.translated_from).map(([code, hashes]) => [
        code,
        Object.fromEntries(Object.entries(hashes).map(([key, hash]) => [key, before.has(key) && textHash(before.get(key)!) === hash ? (after.get(key) ?? hash) : hash])),
      ]),
    )
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
    const before = new Map(formTexts(current).map(item => [item.key, item.text]))
    const oldTexts = Object.fromEntries(before)
    const swapped = translateSchema(current, code)
    const { [code]: _promoted, ...others } = current.translations ?? {}
    const { [code]: _promotedFrom, ...othersFrom } = current.translated_from ?? {}
    const newSource = Object.fromEntries(formTexts(swapped).map(item => [item.key, textHash(item.text)]))
    current.pages = swapped.pages
    current.thank_you = swapped.thank_you
    if (swapped.theme) current.theme = swapped.theme
    current.settings = { ...swapped.settings, language: code, languages: [...extras.value.filter(item => item !== code), old] }
    current.translations = { ...others, [old]: oldTexts }
    current.translated_from = { ...othersFrom, [old]: newSource }
    rebase(before)
  }

  return { main, extras, formTitle, add, remove, set, confirm, promote, rebase }
}
