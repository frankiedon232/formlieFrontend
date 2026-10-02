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
  name: string
  dir: 'ltr' | 'rtl'
  uiLocale: string
}

export const DEFAULT_LOCALE = 'en'

export const LOCALE_COOKIE = 'formalie_locale'

export const APP_LOCALES: AppLocale[] = [
  { code: 'en', language: 'en-US', name: 'English', dir: 'ltr', uiLocale: 'en' },
  { code: 'fr', language: 'fr-FR', name: 'Français', dir: 'ltr', uiLocale: 'fr' },
  { code: 'es', language: 'es-ES', name: 'Español', dir: 'ltr', uiLocale: 'es' },
  { code: 'pt', language: 'pt-BR', name: 'Português', dir: 'ltr', uiLocale: 'pt_br' },
  { code: 'de', language: 'de-DE', name: 'Deutsch', dir: 'ltr', uiLocale: 'de' },
  { code: 'it', language: 'it-IT', name: 'Italiano', dir: 'ltr', uiLocale: 'it' },
  { code: 'nl', language: 'nl-NL', name: 'Nederlands', dir: 'ltr', uiLocale: 'nl' },
  { code: 'pl', language: 'pl-PL', name: 'Polski', dir: 'ltr', uiLocale: 'pl' },
  { code: 'ru', language: 'ru-RU', name: 'Русский', dir: 'ltr', uiLocale: 'ru' },
  { code: 'uk', language: 'uk-UA', name: 'Українська', dir: 'ltr', uiLocale: 'uk' },
  { code: 'tr', language: 'tr-TR', name: 'Türkçe', dir: 'ltr', uiLocale: 'tr' },
  { code: 'ar', language: 'ar-SA', name: 'العربية', dir: 'rtl', uiLocale: 'ar' },
  { code: 'hi', language: 'hi-IN', name: 'हिन्दी', dir: 'ltr', uiLocale: 'hi' },
  { code: 'bn', language: 'bn-BD', name: 'বাংলা', dir: 'ltr', uiLocale: 'bn' },
  { code: 'zh-CN', language: 'zh-CN', name: '简体中文', dir: 'ltr', uiLocale: 'zh_cn' },
  { code: 'ja', language: 'ja-JP', name: '日本語', dir: 'ltr', uiLocale: 'ja' },
  { code: 'ko', language: 'ko-KR', name: '한국어', dir: 'ltr', uiLocale: 'ko' },
  { code: 'id', language: 'id-ID', name: 'Bahasa Indonesia', dir: 'ltr', uiLocale: 'id' },
  { code: 'vi', language: 'vi-VN', name: 'Tiếng Việt', dir: 'ltr', uiLocale: 'vi' },
  { code: 'sw', language: 'sw-KE', name: 'Kiswahili', dir: 'ltr', uiLocale: 'en' },
]
