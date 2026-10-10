/**
 * Request titles in the reader's language (F19): a title Formalie wrote ("Analysis of …", "Check my form")
 * is translated from its code; what someone typed or made (a question, a form's name) stays as it is.
 */
import type { AiRequestRow } from '#shared/types/ai'
import { APP_LOCALES } from '#shared/utils/i18n/locales'

export function useAiText() {
  const { t } = useI18n()
  const languageName = (code: string) => APP_LOCALES.find(locale => locale.code === code)?.name ?? code

  function titleOf(row: Pick<AiRequestRow, 'title' | 'title_key'>): string {
    const key = row.title_key
    if (!key) return row.title
    if (key.code.startsWith('assist_')) return t(`ai.assist.action.${key.code.slice('assist_'.length)}`)
    const params: Record<string, string | number> = { ...key.params }
    if (key.code === 'translate') params.languages = String(params.languages ?? '').split(',').filter(Boolean).map(languageName).join(', ')
    if (key.code === 'rewrite') params.tone = t(`ai.rewrite.tone.${params.tone}`)
    return t(`ai.title.${key.code}`, params)
  }

  /** What was asked: the person's own words, or (for requests Formalie phrased) the translated title. */
  const askedOf = (row: Pick<AiRequestRow, 'title' | 'title_key' | 'kind'> & { prompt: string }) => (row.title_key && !['form', 'template', 'question'].includes(row.kind) ? titleOf(row) : row.prompt)

  return { titleOf, askedOf }
}
