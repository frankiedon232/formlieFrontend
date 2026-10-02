import type {
  AuthTokens,
  LoginChallenge,
  OtpChannel,
  SignupComplete,
  WorkspaceLink,
} from '#shared/types/auth'

export type ChallengePurpose = 'login' | 'signup' | 'find' | 'reset'

export interface PendingChallenge {
  purpose: ChallengePurpose
  email: string
  challenge: LoginChallenge
  /** Mock only: the code the mock just "sent" (shown on the code screen in dev). */
  devCode: string | null
  /** Where to go after a successful login. */
  redirect?: string
}

/** In memory only: a reload on the code screen sends the user back to start (by design). */
const pending = shallowRef<PendingChallenge | null>(null)
let restoring: Promise<boolean> | null = null
let restored = false

const devCodeOf = (meta: Record<string, unknown>) =>
  typeof meta.dev_code === 'string' ? meta.dev_code : null

/**
 * Every sign-in flow (docs/SECURITY-PROTOCOL.md §7): credentials → OTP challenge → tokens.
 * Tokens land in useSession (memory); the refresh token is the server's HttpOnly cookie.
 */
export function useAuth() {
  const api = useApi()
  const session = useSession()
  const tenant = useTenant()

  /** Restore the session after a reload via the refresh cookie (once per page load). */
  function restore(): Promise<boolean> {
    if (restored || session.isAuthenticated.value) return Promise.resolve(session.isAuthenticated.value)
    restoring ??= api
      .post<AuthTokens>('/auth/refresh', undefined, { skipAuthRefresh: true })
      .then(({ data }) => {
        session.applyTokens(data)
        return true
      })
      .catch(() => false)
      .finally(() => {
        restored = true
        restoring = null
      })
    return restoring
  }

  function setPending(
    purpose: ChallengePurpose,
    email: string,
    response: { data: LoginChallenge; meta: Record<string, unknown> },
    redirect?: string,
  ) {
    pending.value = { purpose, email, challenge: response.data, devCode: devCodeOf(response.meta), redirect }
  }

  async function login(email: string, password: string, redirect?: string) {
    const response = await api.post<LoginChallenge>('/auth/login', { email, password })
    setPending('login', email, response, redirect)
  }

  /** Verify the pending code. Login → signed in; other purposes return their own result. */
  async function verify(code: string) {
    const current = pending.value
    if (!current) throw new ApiError('FRM-AUTH-1003', 'Invalid or expired code.')
    const body = { challenge_id: current.challenge.challenge_id, code }
    if (current.purpose === 'find') {
      return (await api.post<WorkspaceLink[]>('/tenants/find-workspace/verify', body)).data
    }
    if (current.purpose === 'signup') {
      await api.post('/auth/otp/verify', body)
      return true
    }
    const { data } = await api.post<AuthTokens>('/auth/otp/verify', body)
    session.applyTokens(data)
    tenant.rememberWorkspace()
    restored = true
    pending.value = null
    return true
  }

  async function resend(channel?: OtpChannel) {
    const current = pending.value
    if (!current) return
    const response = await api.post<LoginChallenge>('/auth/otp/resend', {
      challenge_id: current.challenge.challenge_id,
      channel,
    })
    setPending(current.purpose, current.email, response, current.redirect)
  }

  async function signup(input: { first_name: string; last_name: string; email: string; password: string }) {
    const response = await api.post<LoginChallenge>('/auth/signup', input)
    setPending('signup', input.email, response)
  }

  /** Creates the workspace; resolves to the new workspace URL (one-time ticket inside). */
  async function completeSignup(companyName: string, subdomain: string) {
    const current = pending.value
    if (!current || current.purpose !== 'signup')
      throw new ApiError('FRM-AUTH-1003', 'Invalid or expired code.')
    const { data } = await api.post<SignupComplete>('/auth/signup/complete', {
      challenge_id: current.challenge.challenge_id,
      company_name: companyName,
      subdomain,
    })
    pending.value = null
    return data.redirect_url
  }

  async function exchangeTicket(ticket: string) {
    const { data } = await api.post<AuthTokens>('/auth/exchange-ticket', { ticket })
    session.applyTokens(data)
    tenant.rememberWorkspace()
    restored = true
  }

  async function findWorkspace(email: string) {
    const response = await api.post<LoginChallenge>('/tenants/find-workspace', { email })
    setPending('find', email, response)
  }

  async function forgotPassword(email: string) {
    const response = await api.post<LoginChallenge>('/auth/password/forgot', { email })
    setPending('reset', email, response)
  }

  async function resetPassword(code: string, password: string) {
    const current = pending.value
    if (!current || current.purpose !== 'reset')
      throw new ApiError('FRM-AUTH-1003', 'Invalid or expired code.')
    await api.post('/auth/password/reset', { challenge_id: current.challenge.challenge_id, code, password })
    pending.value = null
  }

  async function logout() {
    try {
      await api.post('/auth/logout')
    } catch {
      // Signing out locally must work even if the server is unreachable.
    } finally {
      session.clear()
      api.resetSecureSession()
      restored = true
    }
  }

  return {
    pending: readonly(pending),
    clearPending: () => (pending.value = null),
    restore,
    login,
    verify,
    resend,
    signup,
    completeSignup,
    exchangeTicket,
    findWorkspace,
    forgotPassword,
    resetPassword,
    logout,
  }
}
