/**
 * Access token in a plain module-level ref (CLAUDE.md rule 12): client memory only — never
 * localStorage, never useState, so it can't leak into an SSR payload. The refresh token is an
 * HttpOnly cookie the browser sends to /auth/refresh by itself. F3 adds user/tenant data here.
 */
const accessToken = ref<string | null>(null)
const expiresAt = ref<number | null>(null)

export function useSession() {
  function setAccessToken(token: string, expiresInSeconds?: number) {
    accessToken.value = token
    expiresAt.value = expiresInSeconds ? Date.now() + expiresInSeconds * 1000 : null
  }

  function clear() {
    accessToken.value = null
    expiresAt.value = null
  }

  return {
    accessToken: readonly(accessToken),
    isAuthenticated: computed(() => !!accessToken.value),
    setAccessToken,
    clear,
  }
}
