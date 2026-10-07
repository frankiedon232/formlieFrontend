/**
 * The request being handled, for helpers deep inside routes (F14 M7): which organisation the person
 * narrowed the portal to (header from the rail's switcher; absent = all).
 */
import { AsyncLocalStorage } from 'node:async_hooks'
import type { H3Event } from 'h3'
import { ORGANISATION_HEADER } from '#shared/types/organisations'
import { decodeId } from './ids'

export const requestScope = new AsyncLocalStorage<H3Event>()

/** The organisation id lists are narrowed to, or null for all. */
export function scopedOrganisation(): string | null {
  const event = requestScope.getStore()
  const value = event ? getHeader(event, ORGANISATION_HEADER) : undefined
  return value ? (decodeId(value) ?? value) : null
}
