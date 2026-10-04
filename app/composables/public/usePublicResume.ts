/**
 * Save and resume on a public form (F10 M2), only when the form has it on:
 *   - answers are saved on the server shortly after each change (a draft under a random token);
 *   - the token lives in this tab only (sessionStorage) and in the respondent's resume link;
 *     a `?resume=` link restores the answers and page, then the token leaves the address bar;
 *   - "Save and continue later" sends the link to an email (the dev mock returns it on screen);
 *   - submitting closes the draft (see usePublicSubmit: resume_token).
 */
export function usePublicResume(key: string, enabled: Ref<boolean>) {
  const api = useApi()
  const { handle } = useErrorHandler()
  const storageKey = `formalie:resume:${key}`
  const base = `/public/forms/${encodeURIComponent(key)}/sessions`

  const token = ref<string | null>(null)
  const initial = ref<{ data: Record<string, unknown>; page: number } | null>(null)
  const state = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const savedAt = ref<string | null>(null)

  const remember = (value: string | null) => {
    token.value = value
    try {
      if (value) sessionStorage.setItem(storageKey, value)
      else sessionStorage.removeItem(storageKey)
    } catch {
      // The draft still works for this page view.
    }
  }

  async function restore() {
    if (!enabled.value || restored) return
    restored = true
    const url = new URL(location.href)
    const fromLink = url.searchParams.get('resume')
    let stored: string | null = null
    try {
      stored = sessionStorage.getItem(storageKey)
    } catch {
      stored = null
    }
    const found = fromLink || stored
    if (fromLink) {
      // Keep the token out of the address bar (history, screenshots, shared tabs).
      url.searchParams.delete('resume')
      history.replaceState(history.state, '', url.pathname + url.search + url.hash)
    }
    if (!found) return
    try {
      const { data } = await api.get<{ data: Record<string, unknown>; page: number; updated_at: string }>(`${base}/${encodeURIComponent(found)}`)
      remember(found)
      initial.value = { data: data.data, page: data.page }
      savedAt.value = data.updated_at
      state.value = 'saved'
    } catch {
      remember(null) // Closed, expired or unknown: start fresh.
    }
  }
  let restored = false
  onMounted(restore)
  // A password form gets its questions (and Save and resume) after the password.
  watch(enabled, on => on && void restore())

  let pending: { data: Record<string, unknown>; page: number } | null = null
  let timer: ReturnType<typeof setTimeout> | undefined
  // One save at a time: a second one waits, so a slow first save never makes a second draft.
  let queue: Promise<unknown> = Promise.resolve()
  function flush(email?: string) {
    const run = queue.then(() => saveNow(email))
    queue = run.catch(() => undefined)
    return run
  }
  async function saveNow(email?: string) {
    if (!enabled.value || !pending) return null
    const body = { ...pending, ...(email ? { email } : {}) }
    state.value = 'saving'
    try {
      const reply = token.value
        ? await api.put<{ saved_at: string; sent_to: string | null }>(`${base}/${encodeURIComponent(token.value)}`, body, { background: true })
        : await api.post<{ resume_token: string; sent_to: string | null }>(base, body, { background: true })
      if ('resume_token' in reply.data) remember(reply.data.resume_token)
      savedAt.value = new Date().toISOString()
      state.value = 'saved'
      return reply
    } catch (error) {
      state.value = 'error'
      if (email) handle(error)
      return null
    }
  }
  /** Called by the form on every change; saves a moment later. */
  function save(data: Record<string, unknown>, page: number) {
    if (!enabled.value) return
    pending = { data, page }
    clearTimeout(timer)
    timer = setTimeout(() => void flush(), 1500)
  }
  /** "Save and continue later": save now and send the link to this email. */
  async function later(email: string): Promise<{ sentTo: string | null; devUrl: string | null } | null> {
    clearTimeout(timer)
    // Nothing typed yet and no draft: still save (empty, page 1), so the link always arrives.
    if (!pending && !token.value) pending = { data: {}, page: 0 }
    const reply = await flush(email)
    if (!reply) return null
    const data = reply.data as { sent_to?: string | null }
    const devUrl = typeof reply.meta?.dev_resume_url === 'string' ? reply.meta.dev_resume_url : null
    return { sentTo: data.sent_to ?? null, devUrl }
  }
  /** After submitting: the draft is closed on the server; forget it here. */
  function finished() {
    clearTimeout(timer)
    pending = null
    remember(null)
    state.value = 'idle'
  }
  onBeforeUnmount(() => clearTimeout(timer))

  return { token, initial, state, savedAt, save, later, finished }
}
