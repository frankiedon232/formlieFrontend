import type { PublicForm, PublicSubmitResult, RendererSubmitOutcome } from '#shared/types/public'

/** Server-only header for the internal page route (server/routes/_ssr). */
const INTERNAL_TOKEN_HEADER = 'x-formalie-internal'

/**
 * A public form page's data (F10). While the page renders on the server it reads the published
 * form through the internal route (server-only token — browsers never see it), so the first
 * response already holds the whole form. In the browser (later visits within the app) it falls
 * back to the enveloped public API.
 */
export async function usePublicForm(key: string) {
  const config = useRuntimeConfig()
  const requestFetch = import.meta.server ? useRequestFetch() : null
  const host = import.meta.server ? useRequestURL().host : ''
  const api = useApi()
  // The renderer takes the workspace's logo and brand colour from the tenant profile.
  // (Composables first: after an await this function no longer has Nuxt's context.)
  const profile = useState<import('#shared/types/auth').TenantPublicProfile | null>('tenant:profile')

  const { data, refresh } = await useAsyncData(`public-form:${key}`, async () => {
    if (import.meta.server && requestFetch) {
      return requestFetch<{ data?: PublicForm; error?: { code: string } }>(`/_ssr/public-forms/${encodeURIComponent(key)}`, {
        headers: { [INTERNAL_TOKEN_HEADER]: String(config.internalToken ?? ''), 'x-forwarded-host': host },
        ignoreResponseError: true,
      })
    }
    try {
      return { data: (await api.get<PublicForm>(`/public/forms/${encodeURIComponent(key)}`)).data }
    } catch (error) {
      return { error: { code: (error as { code?: string }).code ?? 'FRM-GEN-5000' } }
    }
  })

  const form = computed(() => data.value?.data ?? null)
  const errorCode = computed(() => data.value?.error?.code ?? null)

  watchEffect(() => {
    const workspace = form.value?.workspace
    if (!workspace || profile.value?.mode === 'tenant') return
    profile.value = {
      mode: 'tenant',
      name: workspace.name,
      subdomain: workspace.subdomain ?? '',
      logo_url: workspace.logo_url,
      colors: { primary: workspace.primary },
      auth_providers: [],
      status: 'active',
    }
  })

  return { form, errorCode, refresh }
}

/**
 * Sending a public form: one submission id per fill-in session (kept in sessionStorage so a reload
 * or a retry sends the same id — the API answers repeats with the same response, never a second one).
 */
export function usePublicSubmit(key: string, channel: 'link' | 'embed') {
  const api = useApi()
  const { locale } = useI18n()
  const { handle } = useErrorHandler()
  const storageKey = `formalie:submission:${key}`

  function submissionId(): string {
    try {
      const existing = sessionStorage.getItem(storageKey)
      if (existing) return existing
      const fresh = crypto.randomUUID()
      sessionStorage.setItem(storageKey, fresh)
      return fresh
    } catch {
      return (memoryId ??= crypto.randomUUID())
    }
  }
  let memoryId: string | undefined

  async function submit(answers: Record<string, unknown>): Promise<RendererSubmitOutcome> {
    try {
      const { data } = await api.post<PublicSubmitResult>(
        `/public/forms/${encodeURIComponent(key)}/submit`,
        { data: answers, channel, language: locale.value },
        { headers: { 'Idempotency-Key': submissionId() } },
      )
      try {
        sessionStorage.removeItem(storageKey) // A next fill-in is a new session.
      } catch {
        memoryId = undefined
      }
      return { done: true, thank_you: data.thank_you }
    } catch (error) {
      const failure = error as { code?: string; details?: { field?: string; message: string }[] }
      if (failure.code === 'FRM-RESP-1001' && failure.details?.length)
        return { done: false, issues: failure.details.filter(d => d.field).map(d => ({ key: d.field!, code: d.message })) }
      handle(error)
      return { done: false }
    }
  }

  return { submit }
}
