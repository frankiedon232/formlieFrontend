import { DEFAULT_LOCALE } from '../app/utils/locales'

// A missing key in any language falls back to English, so a new string never breaks a page.
export default defineI18nConfig(() => ({
  fallbackLocale: DEFAULT_LOCALE,
  missingWarn: false,
  fallbackWarn: false,
}))
