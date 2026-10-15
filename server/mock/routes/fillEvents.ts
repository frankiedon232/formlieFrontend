/**
 * Fill-in analytics events (owner decision 2026-10-15, docs/API-CONTRACT.md → Public).
 *
 *   POST /public/forms/:key/events { session, kind: view|start|answer|page, field?, page?, channel: link|embed } → {}
 *
 * No sign-in; enveloped like the other public form routes. Only forms that take responses on that
 * channel (the same check as submit). Repeats of the same session + kind (+ field / page) are
 * ignored and still answer {}. Rate-limited per address and form. Nothing personal is stored:
 * no IP, only the random visit id.
 */
import { z } from 'zod'
import { normaliseFillEvent } from '#shared/utils/analytics/events'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { recordFillEvent } from '../data/fillEventStore'
import { takingResponses } from './publicForms'

const eventBody = z.object({
  session: z.string().max(100),
  kind: z.enum(['view', 'start', 'answer', 'page']),
  field: z.string().max(100).optional(),
  page: z.number().int().min(0).max(999).optional(),
  channel: z.enum(['link', 'embed']).default('link'),
})

/** Per address and form: a long form sends one event per question and page, so the cap is generous. */
const EVENTS_PER_10_MIN = 600
const sentBy = new Map<string, number[]>()

export const recordEvent = defineMockRoute(({ event, body }) => {
  const key = getRouterParam(event, 'key') ?? ''
  const input = parseBody(eventBody, body)
  const checked = normaliseFillEvent(input)
  if (!checked) throw new MockError('FRM-GEN-1002', [{ field: input.kind === 'answer' ? 'field' : 'session', message: 'invalid' }])
  const { form } = takingResponses(event, key, { ignoreLimit: true, channel: checked.channel })
  // The address is only used for this in-memory counter, never stored with the event.
  const sender = `${form.id}:${getRequestIP(event, { xForwardedFor: true }) ?? 'unknown'}`
  const recent = (sentBy.get(sender) ?? []).filter(time => time > Date.now() - 600_000)
  if (recent.length >= EVENTS_PER_10_MIN) throw new MockError('FRM-GEN-1029')
  sentBy.set(sender, [...recent, Date.now()])
  recordFillEvent(form.id, { ...checked, at: new Date().toISOString() })
  return ok({})
})
