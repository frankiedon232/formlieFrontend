import type { AuthTokens, SessionOrganisation, SessionTenant, SessionUser } from '#shared/types/auth'

/**
 * Signed-in session in plain module-level refs (CLAUDE.md rule 12): client memory only, never
 * localStorage, never useState, so nothing leaks into an SSR payload. The refresh token is an
 * HttpOnly cookie the browser sends to /auth/refresh by itself; a reload restores the session
 * through it (useAuth().restore()).
 */
const accessToken = ref<string | null>(null)
const expiresAt = ref<number | null>(null)
const user = ref<SessionUser | null>(null)
const tenant = ref<SessionTenant | null>(null)
const organisation = ref<SessionOrganisation | null>(null)

export function useSession() {
  function setAccessToken(token: string, expiresInSeconds?: number) {
    accessToken.value = token
    expiresAt.value = expiresInSeconds ? Date.now() + expiresInSeconds * 1000 : null
  }

  function applyTokens(tokens: AuthTokens) {
    setAccessToken(tokens.access_token, tokens.expires_in)
    user.value = tokens.user
    tenant.value = tokens.tenant
    organisation.value = tokens.organisation
  }

  /** After My profile changes (F16 M5): name, photo and preferences, without a new sign-in. */
  function updateUser(values: Partial<SessionUser>) {
    if (user.value) user.value = { ...user.value, ...values }
  }

  function clear() {
    accessToken.value = null
    expiresAt.value = null
    user.value = null
    tenant.value = null
    organisation.value = null
  }

  const displayName = computed(() =>
    user.value ? `${user.value.first_name} ${user.value.last_name}`.trim() || user.value.email : '',
  )

  return {
    accessToken: readonly(accessToken),
    user: readonly(user),
    tenant: readonly(tenant),
    organisation: readonly(organisation),
    displayName,
    updateUser,
    isAuthenticated: computed(() => !!accessToken.value),
    setAccessToken,
    applyTokens,
    clear,
  }
}
