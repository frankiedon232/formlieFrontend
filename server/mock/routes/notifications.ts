/**
 * Notifications (F14 M4, docs/API-CONTRACT.md → Notifications): the signed-in person's feed.
 *
 *   GET    /notifications                 newest first (100), unread count; announces due events first
 *   POST   /notifications/read            { ids } or { all: true }
 *   DELETE /notifications/read            clears the ones already read
 *   POST   /notifications/digest/send     admins: send the waiting daily summaries now
 *
 * Due events are found when the feed is read (the mock has no scheduler): forms closing within a day,
 * exports that finished.
 */
import { z } from 'zod'
import type { NotificationFeed } from '#shared/types/notifications'
import { requireAdmin, requireAuth } from '../core/auth'
import { encodeId } from '../core/ids'
import { ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { formsOf } from '../data/formStore'
import { announceOnce, clearRead, feedOf, flushDigest, markRead, notify } from '../data/notificationStore'
import type { MockTenant } from '../data/tenants'
import type { H3Event } from 'h3'
import { readyExports } from './responseExports'

const DAY = 86_400_000

function announceDue(event: H3Event, tenant: MockTenant) {
  const now = Date.now()
  for (const form of formsOf(tenant).forms) {
    const closes = form.closes_at ? Date.parse(form.closes_at) : NaN
    if (form.status === 'published' && closes > now && closes - now <= DAY && announceOnce(tenant, `closing:${form.id}:${form.closes_at}`))
      notify(event, tenant, 'form_closing', { form: form.name, date: form.closes_at! }, `/forms/${encodeId(form.id)}/share`)
  }
  for (const item of readyExports(tenant.id))
    if (announceOnce(tenant, `export:${item.id}`)) notify(event, tenant, 'export_ready', { file: item.file_name, form: item.form.name }, '/responses/exports', { only: [item.created_by.id] })
  flushDigest(event, tenant)
}

export const getFeed = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  announceDue(event, tenant)
  return ok<NotificationFeed>(feedOf(tenant, user.id))
})

const readSchema = z.union([z.object({ ids: z.array(z.string().max(64)).min(1).max(200) }), z.object({ all: z.literal(true) })])

export const readNotifications = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const input = parseBody(readSchema, body)
  markRead(tenant, user.id, 'all' in input ? 'all' : input.ids)
  return ok(feedOf(tenant, user.id))
})

export const clearNotifications = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  clearRead(tenant, user.id)
  return ok(feedOf(tenant, user.id))
})

export const sendDigest = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok({ sent: flushDigest(event, tenant, true) })
})
