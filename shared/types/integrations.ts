/**
 * Webhooks and Formalie's own API keys (F13 M6, docs/API-CONTRACT.md → Integrations). Webhooks send
 * each response event to the organisation's own address, signed and retried; API keys let their code
 * read and write responses through their API service endpoints. Admins only until F22.
 */

export const WEBHOOK_EVENTS = ['response.created', 'response.updated', 'response.status_changed', 'response.deleted'] as const
export type WebhookEvent = (typeof WEBHOOK_EVENTS)[number]
/** active · failing (the last delivery failed, retries running) · paused (by someone, or after too many failures). */
export type WebhookStatus = 'active' | 'failing' | 'paused'
export type WebhookDeliveryStatus = 'delivered' | 'retrying' | 'failed'

export interface DailyCount {
  date: string
  count: number
}

export interface Webhook {
  id: string
  name: string
  url: string
  events: WebhookEvent[]
  /** Forms it listens to; empty = every form. */
  forms: { id: string; name: string }[]
  enabled: boolean
  status: WebhookStatus
  /** Why it is paused: by someone, or automatically after repeated failures. */
  paused_reason: 'manual' | 'failures' | null
  /** The webhook token it sends as Authorization: Bearer (made in Tokens & headers); null when it was deleted. */
  token: { id: string; name: string; preview: string; status: string } | null
  deliveries_30d: number
  failed_30d: number
  /** Share delivered on the first or a later try, 0–1; null without deliveries. */
  success_rate: number | null
  avg_ms: number | null
  last_delivery: { at: string; ok: boolean; status_code: number | null } | null
  consecutive_failures: number
  daily: DailyCount[]
  created_by: { id: string; name: string }
  created_at: string
  updated_at: string
}

export interface WebhookSaveRequest {
  name: string
  url: string
  events: WebhookEvent[]
  form_ids: string[]
  enabled?: boolean
  /** A webhook token's id, or 'new' to make one named after the webhook. */
  token_id?: string
}

/** A new webhook, with the token it sends when one was made for it (shown once here; again later after the password). */
export interface WebhookCreated {
  webhook: Webhook
  token: { id: string; name: string; secret: string } | null
}

export interface WebhookAttempt {
  at: string
  status_code: number | null
  duration_ms: number
  /** timeout · refused · dns · tls · or the answer's status text. */
  error: string | null
}

export interface WebhookDelivery {
  id: string
  webhook: { id: string; name: string; url: string }
  event: WebhookEvent | 'ping'
  status: WebhookDeliveryStatus
  attempts: number
  status_code: number | null
  duration_ms: number | null
  at: string
  next_retry_at: string | null
  test: boolean
  form: { id: string; name: string } | null
  response_id: string | null
}

export interface WebhookDeliveryDetail extends WebhookDelivery {
  /** What was sent: headers (the signature masked) and the JSON body (personal answers masked). */
  request: { headers: Record<string, string>; body: string }
  /** The receiver's last answer (first 2,000 characters). */
  response: { headers: Record<string, string>; body: string | null } | null
  history: WebhookAttempt[]
}

export interface WebhookInsights {
  total: number
  by_status: Record<WebhookStatus, number>
  deliveries_30d: number
  previous_30d: number
  failed_30d: number
  success_rate: number | null
  daily: DailyCount[]
}

