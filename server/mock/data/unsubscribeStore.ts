/**
 * Unsubscribes in the mock (owner, 2026-10-12): who stopped which optional emails, per workspace, kept in
 * `.data/mock/unsubscribes.json`. A link carries a signed token (workspace, address, kind, ref), so it works without
 * signing in and only for that address; sendEmail skips an address that stopped that kind of email.
 */
import { createHmac, timingSafeEqual } from 'node:crypto'
import type { UnsubscribeKind } from '#shared/types/emails'
import { UNSUBSCRIBE_KINDS } from '#shared/types/emails'
import { loadPersisted, savePersisted } from '../core/persist'

export interface UnsubscribeTarget {
  tenantId: string
  email: string
  kind: UnsubscribeKind
  /** The form id (new responses) or the event key (notifications). */
  ref: string | null
}

// The mock signs with a fixed development key; the backend uses its own server-side key
const KEY = 'formalie-mock-unsubscribe-v1'
const stopped = new Set<string>(loadPersisted<string[]>('unsubscribes', []))
const save = () => savePersisted('unsubscribes', () => [...stopped])
const slot = (target: UnsubscribeTarget) => [target.tenantId, target.email.trim().toLowerCase(), target.kind, target.ref ?? ''].join('|')
const sign = (payload: string) => createHmac('sha256', KEY).update(payload).digest('base64url').slice(0, 22)

export function unsubscribeToken(target: UnsubscribeTarget): string {
  const payload = Buffer.from(JSON.stringify([target.tenantId, target.email.trim().toLowerCase(), target.kind, target.ref])).toString('base64url')
  return `${payload}.${sign(payload)}`
}

export function readUnsubscribeToken(token: string): UnsubscribeTarget | null {
  const [payload, mac] = token.split('.')
  if (!payload || !mac) return null
  const expected = Buffer.from(sign(payload))
  const given = Buffer.from(mac)
  if (expected.length !== given.length || !timingSafeEqual(expected, given)) return null
  try {
    const [tenantId, email, kind, ref] = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8')) as [string, string, string, string | null]
    if (!(UNSUBSCRIBE_KINDS as readonly string[]).includes(kind)) return null
    return { tenantId, email, kind: kind as UnsubscribeKind, ref }
  } catch {
    return null
  }
}

export const isUnsubscribed = (target: UnsubscribeTarget) => stopped.has(slot(target))

export function setUnsubscribed(target: UnsubscribeTarget, value: boolean) {
  if (value) stopped.add(slot(target))
  else stopped.delete(slot(target))
  save()
}
