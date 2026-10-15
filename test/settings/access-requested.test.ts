import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { DEFAULT_NOTIFICATION_RULES, NOTIFICATION_EVENTS, withNotificationDefaults, type NotificationSettings } from '../../shared/types/notifications'
import { notificationsSchema } from '../../shared/utils/settings/schemas'
import { accessRequestNotice } from '../../server/mock/data/accessRequest'

const locales = join(__dirname, '../../i18n/locales')
const emails = join(__dirname, '../../server/mock/data/emailDefaults')
const files = readdirSync(locales).filter(file => file.endsWith('.json'))
const read = (dir: string, file: string) => JSON.parse(readFileSync(join(dir, file), 'utf8'))

describe('the access_requested notification (owner 2026-10-15)', () => {
  it('comes after security_alert', () => {
    expect(NOTIFICATION_EVENTS.indexOf('access_requested')).toBe(NOTIFICATION_EVENTS.indexOf('security_alert') + 1)
  })
  it('goes to admins, in the app and by email, by default', () => {
    expect(DEFAULT_NOTIFICATION_RULES.access_requested).toEqual({ in_app: true, email: true, to: 'admins', people: [] })
    expect(Object.keys(DEFAULT_NOTIFICATION_RULES).sort()).toEqual([...NOTIFICATION_EVENTS].sort())
  })
  it('is read with its default rule from a section saved before it existed, keeping the saved rules', () => {
    const { access_requested: _new, ...older } = DEFAULT_NOTIFICATION_RULES
    const saved = { events: { ...older, security_alert: { in_app: false, email: false, to: 'everyone', people: [] } }, digest: { enabled: true, hour: 7 } } as unknown as NotificationSettings
    const read = withNotificationDefaults(saved)
    expect(read.events.access_requested).toEqual(DEFAULT_NOTIFICATION_RULES.access_requested)
    expect(read.events.security_alert).toEqual({ in_app: false, email: false, to: 'everyone', people: [] })
    expect(read.digest).toEqual({ enabled: true, hour: 7 })
    // The settings form then saves it like every other event
    expect(notificationsSchema.safeParse(read).success).toBe(true)
    expect(notificationsSchema.safeParse(saved).success).toBe(false)
  })
  it('never shares the default rule object between workspaces', () => {
    const { access_requested: _new, ...older } = DEFAULT_NOTIFICATION_RULES
    const read = withNotificationDefaults({ events: older, digest: { enabled: false, hour: 8 } } as unknown as NotificationSettings)
    read.events.access_requested.email = false
    expect(DEFAULT_NOTIFICATION_RULES.access_requested.email).toBe(true)
  })
})

describe('the mock tells admins when a sign-up waits for approval', () => {
  it('for the workspace\'s link and a personal sign-up link, never for an activation', () => {
    expect(accessRequestNotice('link', 'Sam Lee', 'sam@example.com')).toEqual({ params: { name: 'Sam Lee', email: 'sam@example.com', via: 'link' }, link: '/people?status=pending' })
    expect(accessRequestNotice('invite', 'Kim Park', 'kim@example.com')?.params.via).toBe('invite')
    expect(accessRequestNotice('activation', 'Ana Ruiz', 'ana@example.com')).toBeNull()
  })
  it('names the person by email when they gave no name', () => {
    expect(accessRequestNotice('link', '', 'sam@example.com')?.params.name).toBe('sam@example.com')
  })
})

describe('texts in all 20 languages', () => {
  it('for Settings, the bell, People and single sign-on', () => {
    expect(files).toHaveLength(20)
    for (const file of files) {
      const j = read(locales, file)
      expect(j.settings.notifications.name.access_requested, file).toBeTruthy()
      expect(j.settings.notifications.hint.access_requested, file).toBeTruthy()
      expect(j.settings.notifications.group.people, file).toBeTruthy()
      expect(j.settings.notifications.groupHint.people, file).toBeTruthy()
      expect(j.notifications.event.access_requested.title, file).toBeTruthy()
      expect(j.notifications.event.access_requested.message, file).toMatch(/\{name\}.*\{email\}|\{email\}.*\{name\}/)
      expect(j.people.approve.viaSso, file).toContain('{when}')
      expect(j.settings.sso.domainsNone, file).toBeTruthy()
      expect(j.settings.sso.autoCreateHint, file).toBeTruthy()
    }
  })
  it('for the email, with the name, address and workspace', () => {
    const list = readdirSync(emails).filter(file => file.endsWith('.json'))
    expect(list).toHaveLength(20)
    for (const file of list) {
      const event = read(emails, file).events.access_requested
      expect(event.title, file).toContain('{{name}}')
      for (const name of ['{{name}}', '{{email}}', '{{workspace}}']) expect(event.message, `${file} ${name}`).toContain(name)
    }
  })
  it('for the sign-in page after single sign-on: waiting for approval, and no account', () => {
    for (const file of files) {
      const errors = read(locales, file).errors
      expect(errors['FRM-USER-1010'], file).toBeTruthy()
      expect(errors['FRM-AUTH-1022'], file).toBeTruthy()
    }
  })
})
