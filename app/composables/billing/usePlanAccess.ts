/**
 * What the workspace's plan includes (F24 M3), for pages that offer plan-only things (sign-in methods, single
 * sign-on, custom domain, own sending address, database types): `allows(feature)` and the smallest plan that
 * has it, so the page can show a locked state with a way to the plans instead of failing on save. Uses the
 * shared billing state (loaded once); until it is known everything counts as allowed (the server still checks).
 */
import type { Plan, PlanId } from '#shared/types/billing'
import type { DbEngine } from '#shared/utils/integrations/databases'
import { PLANS } from '#shared/utils/billing/plans'

export type PlanFeatureKey = 'social_signin' | 'sso' | 'custom_domain' | 'custom_email' | 'custom_css' | 'data_residency' | `db:${DbEngine}`

const includes = (plan: Plan, feature: PlanFeatureKey) => {
  if (feature.startsWith('db:')) return plan.limits.databases.includes(feature.slice(3) as DbEngine)
  if (feature === 'custom_domain') return plan.limits.custom_domains !== 0
  return plan.limits[feature as 'social_signin' | 'sso' | 'custom_email' | 'custom_css' | 'data_residency']
}

export function usePlanAccess() {
  const billing = useBilling()
  const { can } = useCan()
  if (!billing.overview.value && can('settings.view')) void billing.load()
  const plan = computed(() => billing.overview.value?.plan ?? null)
  const allows = (feature: PlanFeatureKey) => !plan.value || includes(plan.value, feature)
  /** The first plan that includes it (for "On Professional and up"). */
  const minimumFor = (feature: PlanFeatureKey): PlanId => (billing.plans.value ?? PLANS).find(item => includes(item, feature))?.id ?? 'enterprise'
  return { plan, allows, minimumFor }
}
