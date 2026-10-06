/** How an access rule reads (F13 M3): its kind, its values (countries and regions by name), where it applies. */
import type { ApiAccessRule, ApiRuleKind, ApiRuleScope } from '#shared/types/apiService'

export function useRuleFormat() {
  const { t } = useI18n()
  const { current } = useAppLocale()
  const countries = computed(() => new Intl.DisplayNames([current.value.language], { type: 'region' }))
  const kindLabel = (kind: ApiRuleKind) => t(`apiService.access.kind.${kind}`)
  const kindIcon = (kind: ApiRuleKind) => ({ ip: 'i-lucide-network', domain: 'i-lucide-globe-lock', country: 'i-lucide-flag', region: 'i-lucide-earth' })[kind]
  const valueText = (kind: ApiRuleKind, value: string) => (kind === 'country' ? (countries.value.of(value) ?? value) : kind === 'region' ? t(`apiService.access.region.${value}`) : value)
  /** The first values and how many more ("203.0.113.0/24, 198.51.100.17 +2"). */
  function valuesText(rule: Pick<ApiAccessRule, 'kind' | 'values'>, shown = 2) {
    const names = rule.values.slice(0, shown).map(value => valueText(rule.kind, value))
    return rule.values.length > shown ? `${names.join(', ')} +${rule.values.length - shown}` : names.join(', ')
  }
  const scopeText = (scope: ApiRuleScope) => (scope.type === 'all' ? t('apiService.access.scope.all') : scope.type === 'endpoint' ? `/${scope.name ?? '…'}` : (scope.name ?? '…'))
  return { kindLabel, kindIcon, valueText, valuesText, scopeText }
}
