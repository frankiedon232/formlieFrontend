/**
 * Every address outside the website, from the runtime config (NUXT_PUBLIC_*), never written inline.
 * docs/SIGNUP-FLOW.md, docs/API-HOOKS.md.
 */
export function useSiteLinks() {
  const config = useRuntimeConfig().public

  return {
    site: config.siteUrl,
    portal: config.portalUrl,
    api: (path: string) => apiUrl(config.apiUrl, path),
    signup: (plan?: PlanId, period?: BillingPeriod) => signupUrl(config.portalUrl, plan, period),
    signIn: findWorkspaceUrl(config.portalUrl),
    formEmbed: (key: FormKey, prefill?: Record<string, string | undefined>) =>
      formEmbedUrl(config.formsUrl, key, prefill),
  }
}
