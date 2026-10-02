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
      expect(action.startsWith(`${AUDIT_EVENTS[action].area}.`)).toBe(true)
    }
  })

  it('every action, area and field has a label', () => {
    for (const action of AUDIT_ACTIONS) expect(en.audit.action[auditActionKey(action)], action).toBeTruthy()
    for (const area of AUDIT_AREAS) expect(en.audit.area[area], area).toBeTruthy()
    for (const field of AUDIT_FIELDS) expect(en.audit.field[field], field).toBeTruthy()
  })

  it('has no labels for actions that no longer exist', () => {
    const keys = AUDIT_ACTIONS.map(auditActionKey)
    expect(Object.keys(en.audit.action).sort()).toEqual([...keys].sort())
  })
})
