/**
 * Nuxt UI's own component strings (date pickers, pagination, etc.) per app language.
 * Named imports keep unused Nuxt UI locales out of the bundle.
 */
import type { Locale, Messages } from '@nuxt/ui'
import {
  ar,
  bn,
  de,
  en,
  es,
  fr,
  hi,
  id,
  it,
  ja,
  ko,
  nl,
  pl,
  pt_br,
  ru,
  tr,
  uk,
  vi,
  zh_cn,
} from '@nuxt/ui/locale'

const UI_LOCALES: Record<string, Locale<Messages>> = {
  ar,
  bn,
  de,
  en,
  es,
  fr,
  hi,
  id,
  it,
  ja,
  ko,
  nl,
  pl,
  pt_br,
  ru,
  tr,
  uk,
  vi,
  zh_cn,
}

export function resolveUiLocale(uiKey: string | undefined): Locale<Messages> {
  return (uiKey && UI_LOCALES[uiKey]) || en
}
