/**
 * Unsubscribe links (owner, 2026-10-12), public, no sign-in: the signed token says who and what.
 *   GET  /public/unsubscribe?t=        → UnsubscribeView (what the link stops; nothing changes yet)
 *   POST /public/unsubscribe { t }     → stop it (the page's button: mail scanners that open links change nothing)
 *   POST /public/unsubscribe/undo { t } → start it again
 *   POST /email/one-click?t=           → plain, for mail apps' own Unsubscribe button (List-Unsubscribe-Post)
 * Each change is in the workspace's audit trail.
 */
import { z } from 'zod'
import type { H3Event } from 'h3'
import type { UnsubscribeView } from '#shared/types/emails'
import { maskEmail } from '#shared/utils/forms/identity'
import { anonymousActor, recordAudit } from '../core/audit'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { formsOf } from '../data/formStore'
import { MOCK_TENANTS } from '../data/tenants'
import { isUnsubscribed, readUnsubscribeToken, setUnsubscribed, type UnsubscribeTarget } from '../data/unsubscribeStore'

function resolve(token: unknown) {
  const target = typeof token === 'string' ? readUnsubscribeToken(token) : null
  const tenant = target ? MOCK_TENANTS.find(item => item.id === target.tenantId) : undefined
  if (!target || !tenant) throw new MockError('FRM-GEN-1004')
  return { target, tenant }
}

function view(target: UnsubscribeTarget, tenant: (typeof MOCK_TENANTS)[number]): UnsubscribeView {
  const subject =
    target.kind === 'response_notification' ? (formsOf(tenant).forms.find(form => form.id === target.ref)?.name ?? null) : target.kind === 'notification' ? target.ref : null
  return { workspace: tenant.name, email: maskEmail(target.email), kind: target.kind, subject, unsubscribed: isUnsubscribed(target) }
}

function change(event: H3Event, token: unknown, stop: boolean) {
  const { target, tenant } = resolve(token)
  if (isUnsubscribed(target) !== stop) {
    setUnsubscribed(target, stop)
    recordAudit(event, tenant, { action: stop ? 'settings.email_unsubscribed' : 'settings.email_resubscribed', actor: anonymousActor(target.email), metadata: { kind: target.kind, ...(target.ref ? { ref: target.ref } : {}) } })
  }
  return view(target, tenant)
}

export const getUnsubscribe = defineMockRoute(({ query }) => {
  const { target, tenant } = resolve(query.t)
  return ok(view(target, tenant))
})

const tokenBody = z.object({ t: z.string().min(10).max(600) })
export const unsubscribe = defineMockRoute(({ event, body }) => ok(change(event, parseBody(tokenBody, body).t, true)))
export const resubscribe = defineMockRoute(({ event, body }) => ok(change(event, parseBody(tokenBody, body).t, false)))

/** Mail apps post `List-Unsubscribe=One-Click` here (RFC 8058); plain, no envelope, always a short answer. */
export const oneClick = defineMockRoute(
  ({ event, query }) => {
    change(event, query.t, true)
    return ok({ unsubscribed: true })
  },
  { plain: true },
)
