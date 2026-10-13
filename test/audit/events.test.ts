import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  AUDIT_ACTIONS,
  AUDIT_AREAS,
  AUDIT_EVENTS,
  AUDIT_FIELDS,
  auditActionKey,
} from '../../shared/utils/audit/events'

// English is the source; the locales test checks every other language has the same keys.
const en = JSON.parse(readFileSync(join(__dirname, '../../i18n/locales/en.json'), 'utf8'))

describe('audit event catalogue', () => {
  it('every action belongs to a known area and has an icon', () => {
    for (const action of AUDIT_ACTIONS) {
      expect(AUDIT_AREAS).toContain(AUDIT_EVENTS[action].area)
      expect(AUDIT_EVENTS[action].icon).toMatch(/^i-lucide-/)
      // A key starts with its area; the one exception is Formalie support access, filed under Settings
      const prefix = action.startsWith('support.') ? 'settings' : action.split('.')[0]
      expect(AUDIT_EVENTS[action].area, action).toBe(prefix)
    }
  })

  it('every action, area and field has a label', () => {
    for (const action of AUDIT_ACTIONS) expect(en.audit.action[auditActionKey(action)], action).toBeTruthy()
    for (const area of AUDIT_AREAS) expect(en.audit.area[area], area).toBeTruthy()
    for (const field of AUDIT_FIELDS) expect(en.audit.field[field], field).toBeTruthy()
  })

  it('names what the Formalie team does through the platform admin (B16)', () => {
    const workspace = ['suspended', 'restored', 'read_only', 'closing', 'close_cancelled', 'closed', 'plan_changed', 'subdomain_changed', 'message_sent']
    for (const key of workspace) expect(AUDIT_EVENTS[`workspace.${key}` as keyof typeof AUDIT_EVENTS]?.area, key).toBe('workspace')
    const support = ['access_requested', 'access_granted', 'access_revoked', 'session_started', 'session_ended']
    for (const key of support) expect(AUDIT_EVENTS[`support.${key}` as keyof typeof AUDIT_EVENTS]?.area, key).toBe('settings')
  })

  it('has no labels for actions that no longer exist', () => {
    const keys = AUDIT_ACTIONS.map(auditActionKey)
    expect(Object.keys(en.audit.action).sort()).toEqual([...keys].sort())
  })
})
