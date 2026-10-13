/**
 * DEVELOPMENT ONLY. How a webhook delivery is signed (security review M16, 2026-10-13; docs/API-CONTRACT.md →
 * Webhook deliveries), the same as the backend: `Formalie-Signature: v1=<hex HMAC-SHA256 of "{timestamp}.{raw body}">`,
 * keyed with the webhook token (the value also sent as Authorization: Bearer), and `Formalie-Timestamp` the Unix
 * seconds of this try. Receivers refuse a timestamp more than 5 minutes old.
 */
import { createHmac } from 'node:crypto'

export const webhookSignature = (token: string, timestamp: number, body: string) =>
  `v1=${createHmac('sha256', token).update(`${timestamp}.${body}`).digest('hex')}`

/** The two headers for one try. */
export function signedHeaders(token: string, body: string, now = Date.now()): { 'Formalie-Timestamp': string; 'Formalie-Signature': string } {
  const timestamp = Math.floor(now / 1000)
  return { 'Formalie-Timestamp': String(timestamp), 'Formalie-Signature': webhookSignature(token, timestamp, body) }
}
