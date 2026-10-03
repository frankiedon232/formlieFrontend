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
  // Footer legal links from the platform settings (super admin), shared with the page frame.
  const legal = useState<PublicForm['legal'] | null>('public:legal', () => null)

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
    if (form.value?.legal) legal.value = form.value.legal
  })
  watchEffect(() => {
    const workspace = form.value?.workspace
    if (!workspace || profile.value?.mode === 'tenant') return
    profile.value = {
      mode: 'tenant',
      name: workspace.name,
      subdomain: workspace.subdomain ?? '',
      logo_url: workspace.logo_url,
      colors: { primary: workspace.primary },
      website: workspace.website,
      auth_providers: [],
      status: 'active',
    }
  })

  return { form, errorCode, refresh }
}

/**
 * Sending a public form (F10):
 *   - one submission id per fill-in session (sessionStorage) — a reload or retry sends the same id,
 *     and the API answers repeats with the same response, never a second one;
 *   - this browser remembers it has sent the form (localStorage receipt, not personal data) so a
 *     return visit says so; a new response from the same browser only "for someone else";
 *   - refusals become outcomes the form can show: already sent · exact duplicate · answer taken.
 */
export function usePublicSubmit(key: string, channel: 'link' | 'embed') {
  const api = useApi()
  const { locale } = useI18n()
  const { handle } = useErrorHandler()
  const sessionKey = `formalie:submission:${key}`
  const receiptKey = `formalie:sent:${key}`
  let memoryId: string | undefined

  const alreadySent = ref(false)
  onMounted(() => {
    try {
      alreadySent.value = !!localStorage.getItem(receiptKey)
    } catch {
      alreadySent.value = false
    }
  })
  /** Set when the respondent confirmed the next response is for another person. */
  const forSomeoneElse = ref(false)

  function submissionId(): string {
    try {
      const existing = sessionStorage.getItem(sessionKey)
      if (existing) return existing
      const fresh = crypto.randomUUID()
      sessionStorage.setItem(sessionKey, fresh)
      return fresh
    } catch {
      return (memoryId ??= crypto.randomUUID())
    }
  }
  function newSession() {
    try {
      sessionStorage.removeItem(sessionKey)
    } catch {
      // memory fallback below
    }
    memoryId = undefined
  }

  async function submit(answers: Record<string, unknown>): Promise<RendererSubmitOutcome> {
    try {
      const { data } = await api.post<PublicSubmitResult>(
        `/public/forms/${encodeURIComponent(key)}/submit`,
        { data: answers, channel, language: locale.value, for_someone_else: forSomeoneElse.value || undefined },
        { headers: { 'Idempotency-Key': submissionId() } },
      )
      newSession() // A next fill-in is a new session.
      forSomeoneElse.value = false
      try {
        localStorage.setItem(receiptKey, new Date().toISOString())
      } catch {
        // Without storage the API still refuses a second response from this browser.
      }
      alreadySent.value = true
      return { done: true, thank_you: data.thank_you }
    } catch (error) {
      const failure = error as { code?: string; details?: { field?: string; message: string }[] }
      if (failure.code === 'FRM-RESP-1001' && failure.details?.length)
        return { done: false, issues: failure.details.filter(d => d.field).map(d => ({ key: d.field!, code: d.message })) }
      if (failure.code === 'FRM-RESP-1006' && failure.details?.length)
        return { done: false, issues: failure.details.filter(d => d.field).map(d => ({ key: d.field!, code: 'unique' })) }
      if (failure.code === 'FRM-RESP-1004') return { done: false, reason: 'already' }
      if (failure.code === 'FRM-RESP-1005') return { done: false, reason: 'duplicate' }
      handle(error)
      return { done: false }
    }
  }

  /** "Fill in another" / "for someone else": a fresh session that may be sent from this browser. */
  function another() {
    forSomeoneElse.value = true
    newSession()
  }

  return { submit, alreadySent, another }
}
