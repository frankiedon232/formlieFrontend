/** How a token reads in lists, cards and the panel (F13 M2): its kind, what it may call, when it expires. */
import type { ApiToken } from '#shared/types/apiService'

export function useTokenFormat() {
  const { t } = useI18n()
  const { date, relative } = useFormat()
  const kindLabel = (token: Pick<ApiToken, 'kind'>) => t(`apiService.tokens.kind.${token.kind}`)
  /** "All endpoints", or the services / endpoints it is limited to, then the methods. */
  function scopeText(token: Pick<ApiToken, 'scopes' | 'scope_names' | 'scope_gone'>) {
    const where = [...token.scope_names.services, ...token.scope_names.endpoints.map(name => `/${name}`)]
    const target = where.length ? where.join(', ') : token.scope_gone ? t('apiService.tokens.scope.gone') : t('apiService.tokens.scope.all')
    return token.scopes.methods.length ? `${target} · ${token.scopes.methods.join(', ')}` : target
  }
  const expiresText = (token: Pick<ApiToken, 'expires_at' | 'status'>) =>
    !token.expires_at ? t('apiService.tokens.never') : token.status === 'expired' ? t('apiService.tokens.expiredOn', { date: date(token.expires_at) }) : date(token.expires_at)
  const usedText = (token: Pick<ApiToken, 'last_used_at'>) => (token.last_used_at ? t('apiService.tokens.used', { when: relative(token.last_used_at) }) : t('apiService.tokens.notUsed'))
  /** Worth a look: expiring soon, or not used for 90 days. */
  const flagged = (token: Pick<ApiToken, 'status' | 'last_used_at' | 'created_at'>) =>
    token.status === 'expiring' || (token.status === 'active' && Date.parse(token.last_used_at ?? token.created_at) < Date.now() - 90 * 86_400_000)
  return { kindLabel, scopeText, expiresText, usedText, flagged }
}
