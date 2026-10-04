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
 *   - refusals become outcomes the form can show: already sent · exact duplicate · answer taken;
 *   - spam check (decision 89): a proof-of-work challenge solved in the background + a hidden trap field.
 */
export function usePublicSubmit(key: string, channel: 'link' | 'embed', resume?: { token: Ref<string | null>; finished: () => void }) {
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
    prepareProof()
  })

  // Spam check (decision 89): a challenge from the server, solved in the background while the
  // person fills in; a new one after each response.
  let proof: Promise<{ token: string; nonce: number; ready: number } | null> | null = null
  function prepareProof() {
    proof = (async () => {
      try {
        const { data } = await api.post<{ token: string; salt: string; difficulty: number; min_wait_ms: number }>(
          `/public/forms/${encodeURIComponent(key)}/challenge`,
          undefined,
          { background: true },
        )
        const nonce = await solveWork(data.salt, data.difficulty)
        return nonce == null ? null : { token: data.token, nonce, ready: Date.now() + data.min_wait_ms }
      } catch {
        return null // The submission asks again (FRM-RESP-1009 → one automatic retry).
      }
    })()
  }
  /** Set when the respondent confirmed the next response is for another person. */
  const forSomeoneElse = ref(false)
  /** Set when the respondent confirmed they are not the person of a similar earlier response. */
  const confirmedDifferent = ref(false)
  /** From the email code step, when the form verifies the respondent's email. */
  const verificationToken = ref<string | null>(null)

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

  async function send(answers: Record<string, unknown>, trap: string) {
    if (!proof) prepareProof()
    const solved = await proof
    // A challenge is valid a few seconds after it was issued (people don't fill in a form instantly).
    if (solved && solved.ready > Date.now()) await new Promise(done => setTimeout(done, solved.ready - Date.now()))
    return api.post<PublicSubmitResult>(
      `/public/forms/${encodeURIComponent(key)}/submit`,
      {
        data: answers,
        channel,
        language: locale.value,
        for_someone_else: forSomeoneElse.value || undefined,
        confirmed_different: confirmedDifferent.value || undefined,
        verification_token: verificationToken.value ?? undefined,
        resume_token: resume?.token.value ?? undefined,
        challenge: solved ? { token: solved.token, nonce: solved.nonce } : undefined,
        trap: trap || undefined,
      },
      { headers: { 'Idempotency-Key': submissionId() } },
    )
  }

  async function submit(answers: Record<string, unknown>, extra: { trap?: string } = {}): Promise<RendererSubmitOutcome> {
    try {
      const { data } = await send(answers, extra.trap ?? '').catch(async (error: { code?: string }) => {
        // The challenge was used, expired or couldn't be solved: one fresh try.
        if (error.code !== 'FRM-RESP-1009') throw error
        prepareProof()
        return send(answers, extra.trap ?? '')
      })
      prepareProof()
      newSession() // A next fill-in is a new session.
      resume?.finished()
      forSomeoneElse.value = false
      confirmedDifferent.value = false
      verificationToken.value = null
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
      const detail = failure.details?.[0]
      const hint = (() => {
        try {
          return detail?.message ? (JSON.parse(detail.message) as { at?: string; email?: string }) : undefined
        } catch {
          return undefined
        }
      })()
      if (failure.code === 'FRM-RESP-1006') return { done: false, reason: 'registered', field: detail?.field, hint }
      if (failure.code === 'FRM-RESP-1007') return { done: false, reason: 'possible', field: detail?.field, hint }
      if (failure.code === 'FRM-RESP-1008') return { done: false, reason: 'verify', field: detail?.field, hint: { email: detail?.message } }
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

  /** "Yes, I'm a different person" — send again; the team sees it flagged as a possible duplicate. */
  const confirmDifferent = () => (confirmedDifferent.value = true)

  /** Email code step: send a code, then trade it for a short-lived token. Dev mock returns the code. */
  async function sendCode(email: string): Promise<{ sentTo: string; devCode: string | null } | null> {
    try {
      const { data, meta } = await api.post<{ sent_to: string }>(`/public/forms/${encodeURIComponent(key)}/verify`, { email })
      return { sentTo: data.sent_to, devCode: typeof meta?.dev_code === 'string' ? meta.dev_code : null }
    } catch (error) {
      handle(error)
      return null
    }
  }
  async function confirmCode(email: string, code: string): Promise<boolean> {
    try {
      const { data } = await api.post<{ token: string }>(`/public/forms/${encodeURIComponent(key)}/verify/confirm`, { email, code })
      verificationToken.value = data.token
      return true
    } catch (error) {
      handle(error)
      return false
    }
  }

  return { submit, alreadySent, another, confirmDifferent, sendCode, confirmCode }
}
