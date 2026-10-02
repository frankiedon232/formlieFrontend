/**
 * Single source of truth for supported UI languages.
 * Used by nuxt.config.ts (i18n module), the locale switcher and the
 * Nuxt UI component locale mapping in app.vue.
 *
 * `uiLocale` is the key in `@nuxt/ui/locale`; when Nuxt UI has no translation
 * for a language we fall back to `en` for component-internal strings only.
 */
export interface AppLocale {
  code: string
  language: string
  /** Native name, shown in the switcher. */
  name: string
  /** English name, shown as description and used for search. */
  englishName: string
  dir: 'ltr' | 'rtl'
  uiLocale: string
}

export const DEFAULT_LOCALE = 'en'

export const LOCALE_COOKIE = 'formalie_locale'

export const APP_LOCALES: AppLocale[] = [
  { code: 'en', language: 'en-US', name: 'English', englishName: 'English', dir: 'ltr', uiLocale: 'en' },
  { code: 'fr', language: 'fr-FR', name: 'Français', englishName: 'French', dir: 'ltr', uiLocale: 'fr' },
  { code: 'es', language: 'es-ES', name: 'Español', englishName: 'Spanish', dir: 'ltr', uiLocale: 'es' },
  {
    code: 'pt',
    language: 'pt-BR',
    name: 'Português',
    englishName: 'Portuguese',
    dir: 'ltr',
    uiLocale: 'pt_br',
  },
  { code: 'de', language: 'de-DE', name: 'Deutsch', englishName: 'German', dir: 'ltr', uiLocale: 'de' },
  { code: 'it', language: 'it-IT', name: 'Italiano', englishName: 'Italian', dir: 'ltr', uiLocale: 'it' },
  { code: 'nl', language: 'nl-NL', name: 'Nederlands', englishName: 'Dutch', dir: 'ltr', uiLocale: 'nl' },
  { code: 'pl', language: 'pl-PL', name: 'Polski', englishName: 'Polish', dir: 'ltr', uiLocale: 'pl' },
  { code: 'ru', language: 'ru-RU', name: 'Русский', englishName: 'Russian', dir: 'ltr', uiLocale: 'ru' },
  { code: 'uk', language: 'uk-UA', name: 'Українська', englishName: 'Ukrainian', dir: 'ltr', uiLocale: 'uk' },
  { code: 'tr', language: 'tr-TR', name: 'Türkçe', englishName: 'Turkish', dir: 'ltr', uiLocale: 'tr' },
  { code: 'ar', language: 'ar-SA', name: 'العربية', englishName: 'Arabic', dir: 'rtl', uiLocale: 'ar' },
  { code: 'hi', language: 'hi-IN', name: 'हिन्दी', englishName: 'Hindi', dir: 'ltr', uiLocale: 'hi' },
  { code: 'bn', language: 'bn-BD', name: 'বাংলা', englishName: 'Bengali', dir: 'ltr', uiLocale: 'bn' },
  {
    code: 'zh-CN',
    language: 'zh-CN',
    name: '简体中文',
    englishName: 'Chinese (Simplified)',
    dir: 'ltr',
    uiLocale: 'zh_cn',
  },
  { code: 'ja', language: 'ja-JP', name: '日本語', englishName: 'Japanese', dir: 'ltr', uiLocale: 'ja' },
  { code: 'ko', language: 'ko-KR', name: '한국어', englishName: 'Korean', dir: 'ltr', uiLocale: 'ko' },
  {
    code: 'id',
    language: 'id-ID',
    name: 'Bahasa Indonesia',
    englishName: 'Indonesian',
    dir: 'ltr',
    uiLocale: 'id',
  },
  {
    code: 'vi',
    language: 'vi-VN',
    name: 'Tiếng Việt',
    englishName: 'Vietnamese',
    dir: 'ltr',
    uiLocale: 'vi',
  },
  { code: 'sw', language: 'sw-KE', name: 'Kiswahili', englishName: 'Swahili', dir: 'ltr', uiLocale: 'en' },
]
