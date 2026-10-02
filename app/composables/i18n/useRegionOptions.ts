import { COUNTRY_CODES, CURRENCY_CODES } from '#shared/utils/platform/countries'

/** Country picker items in the active language, with circle flags, sorted by name. */
export function useCountryOptions() {
  const { current } = useAppLocale()
  return computed(() => {
    const names = new Intl.DisplayNames([current.value.language], { type: 'region' })
    const collator = new Intl.Collator(current.value.language)
    return COUNTRY_CODES.map(code => ({
      value: code,
      label: names.of(code) ?? code,
      icon: `i-circle-flags-${code.toLowerCase()}`,
    })).sort((a, b) => collator.compare(a.label, b.label))
  })
}

/** Currency picker items: "EUR — Euro" in the active language. */
export function useCurrencyOptions() {
  const { current } = useAppLocale()
  return computed(() => {
    const names = new Intl.DisplayNames([current.value.language], { type: 'currency' })
    return CURRENCY_CODES.map(code => ({ value: code, label: `${code} — ${names.of(code) ?? code}` }))
  })
}

/** Timezone picker items with their UTC offset, computed once per page. */
export function useTimezoneOptions() {
  return shallowRef(timezoneOptions())
}
