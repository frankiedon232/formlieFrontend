/**
 * Webhook rules shared by the portal and the server (F13 M6): which addresses may receive calls, how
 * a delivery is signed, when it is retried and when a webhook pauses itself.
 */
import type { WebhookEvent, WebhookStatus } from '#shared/types/integrations'
import { ipInCidr, parseIp } from '#shared/utils/apiService/access'
import { isBlockedHost } from '#shared/utils/datasources/engines'

export type WebhookUrlProblem = 'required' | 'url' | 'https' | 'host' | 'private'

/** Private and reserved networks a webhook never calls (server-side request forgery). */
const PRIVATE = ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '100.64.0.0/10', '169.254.0.0/16', '0.0.0.0/8', 'fc00::/7', 'fe80::/10']
const LOCAL = new Set(['localhost', '127.0.0.1', '[::1]', '::1'])

/**
 * An address that may receive webhooks: HTTPS, a public host, never Formalie itself. `allowLocal`
 * (development only) lets `http://localhost` through so a receiver on the developer's machine works.
 */
export function checkWebhookUrl(value: string, options: { allowLocal?: boolean } = {}): WebhookUrlProblem | null {
  const text = value.trim()
  if (!text) return 'required'
  let url: URL
  try {
    url = new URL(text)
  } catch {
    return 'url'
  }
  const host = url.hostname.toLowerCase()
  if (options.allowLocal && LOCAL.has(host) && (url.protocol === 'http:' || url.protocol === 'https:')) return null
  if (url.protocol !== 'https:') return 'https'
  if (url.username || url.password) return 'url'
  if (/(^|\.)formalie\.(dev|com)$/.test(host)) return 'host'
  if (isBlockedHost(host)) return 'private'
  const bare = host.replace(/^\[|\]$/g, '')
  if (parseIp(bare) && PRIVATE.some(range => ipInCidr(bare, range))) return 'private'
  return null
}

/** What is signed: `{timestamp}.{body}` with HMAC-SHA256 and the webhook's secret, sent as `sha256=<hex>`. */
export const signedPayload = (timestamp: number, body: string) => `${timestamp}.${body}`

/** Minutes to wait before each retry (then it is failed for good). */
export const WEBHOOK_RETRY_MINUTES = [1, 5, 15, 60, 360] as const
/** After this many failed deliveries in a row the webhook pauses itself (nothing is lost: they can be sent again). */
export const WEBHOOK_AUTO_PAUSE = 20
/** A receiver has this long to answer. */
export const WEBHOOK_TIMEOUT_MS = 10_000

export function webhookStatusOf(webhook: { enabled: boolean; consecutive_failures: number }): WebhookStatus {
  if (!webhook.enabled) return 'paused'
  return webhook.consecutive_failures > 0 ? 'failing' : 'active'
}

export const eventLabelKey = (event: WebhookEvent | 'ping') => `integrations.webhooks.event.${event.replace('.', '_')}`
