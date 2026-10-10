/**
 * Plan limits in the mock (F24 M3): what the workspace's plan allows, checked where it matters. Over a limit:
 * `402 FRM-PLAN-1001` (a number reached: forms, responses on a form); not in the plan: `402 FRM-PLAN-1002`
 * (a database type, other sign-in methods, single sign-on, a custom domain, an own sending address). Nothing
 * is ever deleted when a plan gets smaller: what goes over keeps working as it is and can't grow.
 */
import type { PlanLimits } from '#shared/types/billing'
import type { DbEngine } from '#shared/utils/integrations/databases'
import { currentPlan } from '../data/billingStore'
import type { MockTenant } from '../data/tenants'
import { MockError } from './respond'

export const limitsOf = (tenant: MockTenant): PlanLimits => currentPlan(tenant).limits

/** Room for one more form? (live forms; the trash doesn't count) */
export function requireFormSlot(tenant: MockTenant, liveForms: number) {
  const { forms } = limitsOf(tenant)
  if (forms !== null && liveForms >= forms) throw new MockError('FRM-PLAN-1001', [{ field: 'forms', message: String(forms) }])
}

/** Does this form still take responses under the plan? */
export const responsesAllowed = (tenant: MockTenant, count: number) => {
  const { responses_per_form: limit } = limitsOf(tenant)
  return limit === null || count < limit
}

export function requireDatabase(tenant: MockTenant, engine: DbEngine) {
  if (!limitsOf(tenant).databases.includes(engine)) throw new MockError('FRM-PLAN-1002', [{ field: 'engine', message: engine }])
}

type Feature = 'social_signin' | 'sso' | 'custom_domain' | 'custom_email' | 'custom_css' | 'data_residency'
export function hasFeature(tenant: MockTenant, feature: Feature) {
  const limits = limitsOf(tenant)
  if (feature === 'custom_domain') return limits.custom_domains !== 0
  return limits[feature]
}
export function requireFeature(tenant: MockTenant, feature: Feature) {
  if (!hasFeature(tenant, feature)) throw new MockError('FRM-PLAN-1002', [{ field: feature, message: feature }])
}
