import { describe, expect, it } from 'vitest'
import type { PlatformAnnouncement } from '../../shared/types/support'
import { errorDetailKey } from '../../app/utils/api/errorDetails'
import { countdownText, msLeft, safeAnnouncementLink, supportTicketFromHash, visibleAnnouncements } from '../../app/utils/support/support'

const TICKET = 'Abc_123-xyzAbc_123-xyzAbc_123-xyz'

describe('supportTicketFromHash', () => {
  it('reads the ticket from the fragment', () => {
    expect(supportTicketFromHash(`#ticket=${TICKET}`)).toBe(TICKET)
    expect(supportTicketFromHash(`ticket=${TICKET}&x=1`)).toBe(TICKET)
  })
  it('refuses a missing, short or long ticket', () => {
    expect(supportTicketFromHash('')).toBeNull()
    expect(supportTicketFromHash(null)).toBeNull()
    expect(supportTicketFromHash('#other=1')).toBeNull()
    expect(supportTicketFromHash('#ticket=short')).toBeNull()
    expect(supportTicketFromHash(`#ticket=${'a'.repeat(101)}`)).toBeNull()
  })
})

describe('countdown', () => {
  it('counts down to the end and never below zero', () => {
    const now = Date.parse('2026-10-12T12:00:00Z')
    expect(msLeft('2026-10-12T12:05:09Z', now)).toBe(309_000)
    expect(msLeft('2026-10-12T11:00:00Z', now)).toBe(0)
    expect(msLeft(null, now)).toBeNull()
    expect(msLeft('not a date', now)).toBeNull()
  })
  it('formats minutes, hours and days', () => {
    expect(countdownText(309_000)).toBe('05:09')
    expect(countdownText(3_909_000)).toBe('1:05:09')
    expect(countdownText(2 * 86_400_000 + 3 * 3_600_000 + 4 * 60_000 + 5_000)).toBe('2d 03:04:05')
    expect(countdownText(-5)).toBe('00:00')
  })
})

describe('visibleAnnouncements', () => {
  const base: PlatformAnnouncement = { id: 'a', kind: 'banner', tone: 'info', title: 'A', body: null, link_url: null, dismissible: true, starts_at: '2026-10-01T00:00:00Z', ends_at: null }
  const now = Date.parse('2026-10-12T00:00:00Z')
  const list: PlatformAnnouncement[] = [
    base,
    { ...base, id: 'b', tone: 'critical', dismissible: false },
    { ...base, id: 'c', starts_at: '2026-11-01T00:00:00Z' },
    { ...base, id: 'd', ends_at: '2026-10-05T00:00:00Z' },
    { ...base, id: 'e', tone: 'warning' },
  ]
  it('shows what is current, critical first', () => {
    expect(visibleAnnouncements(list, [], now).map(item => item.id)).toEqual(['b', 'e', 'a'])
  })
  it('hides dismissed ones, but never one that may not be dismissed', () => {
    expect(visibleAnnouncements(list, ['a', 'b'], now).map(item => item.id)).toEqual(['b', 'e'])
  })
  it('links only to https addresses', () => {
    expect(safeAnnouncementLink('https://formalie.com/news')).toBe('https://formalie.com/news')
    expect(safeAnnouncementLink('javascript:alert(1)')).toBeNull()
    expect(safeAnnouncementLink('http://formalie.com')).toBeNull()
    expect(safeAnnouncementLink(null)).toBeNull()
  })
})

describe('errorDetailKey', () => {
  it('maps support and workspace details of FRM-PERM-1001', () => {
    expect(errorDetailKey('FRM-PERM-1001', [{ field: 'support', message: 'read_only' }])).toBe('errors.detail.supportReadOnly')
    expect(errorDetailKey('FRM-PERM-1001', [{ field: 'support', message: 'not_in_support_sessions' }])).toBe('errors.detail.notInSupportSessions')
    expect(errorDetailKey('FRM-PERM-1001', [{ field: 'workspace', message: 'read_only' }])).toBe('errors.detail.workspaceReadOnly')
    expect(errorDetailKey('FRM-PERM-1001', [{ field: 'workspace', message: 'closing' }])).toBe('errors.detail.workspaceClosing')
  })
  it('leaves everything else to the code', () => {
    expect(errorDetailKey('FRM-PERM-1001', [])).toBeNull()
    expect(errorDetailKey('FRM-PERM-1001', [{ field: 'mode', message: 'grant_read_only' }])).toBeNull()
    expect(errorDetailKey('FRM-GEN-1002', [{ field: 'support', message: 'read_only' }])).toBeNull()
  })
})
