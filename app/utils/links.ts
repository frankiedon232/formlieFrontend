/**
 * Addresses the website links to: the portal (sign-up, sign-in) and Formalie's own published forms.
 * Pure functions, so they are tested without Nuxt; `useSiteLinks()` binds them to the runtime config.
 * docs/SIGNUP-FLOW.md and docs/API-HOOKS.md.
 */

export type PlanId = 'starter' | 'professional' | 'business' | 'enterprise'
export type BillingPeriod = 'monthly' | 'quarterly' | 'annually'

/** Formalie's own published forms (the app's shared/utils/platform/forms.ts). */
export const FORM_KEYS = {
  enterprise: 'FormalieEn',
  support: 'FormalieHp',
} as const

export type FormKey = (typeof FORM_KEYS)[keyof typeof FORM_KEYS]

function trimSlash(url: string): string {
  return url.replace(/\/+$/, '')
}

function withQuery(url: string, query: Record<string, string | undefined>): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value) params.set(key, value)
  }
  const search = params.toString()
  return search ? `${url}?${search}` : url
}

/** Portal sign-up. Starter (or no plan) never carries a period. */
export function signupUrl(portalUrl: string, plan?: PlanId, period?: BillingPeriod): string {
  const paid = plan === 'professional' || plan === 'business'
  return withQuery(`${trimSlash(portalUrl)}/auth/signup`, { plan, period: paid ? period : undefined })
}

/** Sign in: people type their email and get to their workspace. */
export function findWorkspaceUrl(portalUrl: string): string {
  return `${trimSlash(portalUrl)}/auth/find-workspace`
}

/** One of Formalie's own forms, embedded, with the answers the site may prefill. */
export function formEmbedUrl(
  formsUrl: string,
  key: FormKey,
  prefill: Record<string, string | undefined> = {},
): string {
  return withQuery(`${trimSlash(formsUrl)}/${key}/embed`, prefill)
}

/** A public endpoint of the backend API (`/public/plans` …). */
export function apiUrl(base: string, path: string): string {
  return `${trimSlash(base)}/${path.replace(/^\/+/, '')}`
}
