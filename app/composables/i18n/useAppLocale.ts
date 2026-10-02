/** Current language, its Nuxt UI component locale and a switcher, in one place. */
export function useAppLocale() {
  const { locale, setLocale } = useI18n()

  const current = computed(() => APP_LOCALES.find(item => item.code === locale.value) ?? APP_LOCALES[0]!)

  const uiLocale = computed(() => resolveUiLocale(current.value.uiLocale))

  async function changeLocale(code: string) {
    if (code === locale.value || !APP_LOCALES.some(item => item.code === code)) return
    await setLocale(code as typeof locale.value)
  }

  return { locale, current, uiLocale, locales: APP_LOCALES, changeLocale }
}
