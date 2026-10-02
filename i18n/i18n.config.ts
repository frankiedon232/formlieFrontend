import { DEFAULT_LOCALE } from '../shared/utils/i18n/locales'

// Missing keys in any language fall back to English, so a new string never breaks the UI.
export default defineI18nConfig(() => ({
  fallbackLocale: DEFAULT_LOCALE,
  missingWarn: false,
  fallbackWarn: false,
}))
