/**
 * When a form takes responses (F10, owner 2026-10-03): optional "open from" and "open until".
 *   always:   no dates set
 *   open:     within the dates (closes_at may be set: "until …")
 *   scheduled, before opens_at
 *   expired:  after closes_at
 */
export type Availability = 'always' | 'open' | 'scheduled' | 'expired'

export function availabilityOf(window: { opens_at?: string | null; closes_at?: string | null }, now = Date.now()): Availability {
  const opens = window.opens_at ? Date.parse(window.opens_at) : null
  const closes = window.closes_at ? Date.parse(window.closes_at) : null
  if (closes !== null && now >= closes) return 'expired'
  if (opens !== null && now < opens) return 'scheduled'
  return opens === null && closes === null ? 'always' : 'open'
}
