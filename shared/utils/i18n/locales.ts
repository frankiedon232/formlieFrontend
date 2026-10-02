/**
 * Single source of truth for supported UI languages.
 * Used by nuxt.config.ts (i18n module), the locale switchers and the
 * Nuxt UI component locale mapping in app.vue.
 *
 * `uiLocale` is the key in `@nuxt/ui/locale`; when Nuxt UI has no translation
 * for a language we fall back to `en` for component-internal strings only.
 * `flag` is an icon (circle-flags set) — emoji flags don't render on Windows.
 */
export interface AppLocale {
  code: string
  language: string
  /** Native name, shown in the switcher. */
  name: string
  /** English name, shown as description and used for search. */
  englishName: string
  /** Flag icon of the main country for this language variant. */
  flag: string
  dir: 'ltr' | 'rtl'
  uiLocale: string
}

export const DEFAULT_LOCALE = 'en'

export const LOCALE_COOKIE = 'formalie_locale'

type Row = [code: string, language: string, name: string, englishName: string, flag: string, uiLocale: string]

const ROWS: Row[] = [
  ['en', 'en-US', 'English', 'English', 'us', 'en'],
  ['fr', 'fr-FR', 'Français', 'French', 'fr', 'fr'],
  ['es', 'es-ES', 'Español', 'Spanish', 'es', 'es'],
  ['pt', 'pt-BR', 'Português', 'Portuguese', 'br', 'pt_br'],
  ['de', 'de-DE', 'Deutsch', 'German', 'de', 'de'],
  ['it', 'it-IT', 'Italiano', 'Italian', 'it', 'it'],
  ['nl', 'nl-NL', 'Nederlands', 'Dutch', 'nl', 'nl'],
  ['pl', 'pl-PL', 'Polski', 'Polish', 'pl', 'pl'],
  ['ru', 'ru-RU', 'Русский', 'Russian', 'ru', 'ru'],
  ['uk', 'uk-UA', 'Українська', 'Ukrainian', 'ua', 'uk'],
  ['tr', 'tr-TR', 'Türkçe', 'Turkish', 'tr', 'tr'],
  ['ar', 'ar-SA', 'العربية', 'Arabic', 'sa', 'ar'],
  ['hi', 'hi-IN', 'हिन्दी', 'Hindi', 'in', 'hi'],
  ['bn', 'bn-BD', 'বাংলা', 'Bengali', 'bd', 'bn'],
  ['zh-CN', 'zh-CN', '简体中文', 'Chinese (Simplified)', 'cn', 'zh_cn'],
  ['ja', 'ja-JP', '日本語', 'Japanese', 'jp', 'ja'],
  ['ko', 'ko-KR', '한국어', 'Korean', 'kr', 'ko'],
  ['id', 'id-ID', 'Bahasa Indonesia', 'Indonesian', 'id', 'id'],
  ['vi', 'vi-VN', 'Tiếng Việt', 'Vietnamese', 'vn', 'vi'],
  ['sw', 'sw-KE', 'Kiswahili', 'Swahili', 'ke', 'en'],
]

const RTL = new Set(['ar'])

export const APP_LOCALES: AppLocale[] = ROWS.map(([code, language, name, englishName, flag, uiLocale]) => ({
  code,
  language,
  name,
  englishName,
  flag: `i-circle-flags-${flag}`,
  dir: RTL.has(code) ? 'rtl' : 'ltr',
  uiLocale,
}))
