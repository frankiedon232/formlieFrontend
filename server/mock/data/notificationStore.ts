/**
 * Notifications in the mock (F14 M4), kept in `.data/mock/notifications.json`: each person's feed, the
 * daily summaries waiting to go out, and what was already announced. `notify()` follows Settings →
 * Notifications: in the app for the people it names, by email (one each time, or once a day in the
 * summary). Never throws, so an event never breaks the action that caused it.
 */
import type { H3Event } from 'h3'
import type { AppNotification, NotificationEvent, NotificationRule } from '#shared/types/notifications'
import { emailDefaults, emailLanguage, fillIn } from '../core/email'
import { encodeId } from '../core/ids'
import { loadPersisted, savePersisted } from '../core/persist'
import { peopleOf } from './orgStore'
import { sendEmail } from './outboxStore'
import { settingsOf } from './settingsStore'
import { MOCK_USERS, type MockTenant } from './tenants'
import { can } from './rolesStore'

const KEEP = 100

interface StoredNotification extends AppNotification {
  user_id: string
}
interface TenantNotifications {
  items: StoredNotification[]
  /** Daily summary lines waiting, by email address. */
  digest: Record<string, { name: string; lines: string[] }>
  digest_sent_on: string | null
  /** Things announced once (a form closing at a time, an export). */
  announced: string[]
}

const stores = new Map<string, TenantNotifications>(Object.entries(loadPersisted<Record<string, TenantNotifications>>('notifications', {})))
const save = () => savePersisted('notifications', () => Object.fromEntries(stores))

export function notificationsOf(tenant: MockTenant): TenantNotifications {
  let store = stores.get(tenant.id)
  if (!store) {
    store = { items: [], digest: {}, digest_sent_on: null, announced: [] }
    stores.set(tenant.id, store)
  }
  return store
}

/** The workspace's portal address for a path (links in emails). */
export function workspaceUrl(event: H3Event | null, tenant: MockTenant, path: string) {
  const root = event ? useRuntimeConfig(event).public.rootDomain : 'formalie.dev'
  const port = event ? getRequestURL(event).port : ''
  return `https://${tenant.subdomain}.${root}${port ? `:${port}` : ''}${path}`
}

/** Who a rule reaches: members get it in the app, everyone named gets the email. */
function recipients(tenant: MockTenant, rule: NotificationRule, only?: string[]) {
  const users = MOCK_USERS.filter(user => user.tenant_id === tenant.id && !user.disabled)
  if (only) {
    const picked = users.filter(user => only.includes(user.id))
    return { members: picked.map(user => user.id), emails: picked.map(user => ({ email: user.email, name: user.first_name })) }
  }
  if (rule.to === 'people') {
    const people = peopleOf(tenant).filter(person => rule.people.includes(person.id))
    return { members: users.filter(user => rule.people.includes(user.id)).map(user => user.id), emails: people.map(person => ({ email: person.email, name: person.name.split(' ')[0] ?? person.name })) }
  }
  const chosen = rule.to === 'admins' ? users.filter(user => can(user, 'settings.manage')) : users
  return { members: chosen.map(user => user.id), emails: chosen.map(user => ({ email: user.email, name: user.first_name })) }
}

/**
 * Tells the right people about an event. `params` fill the text (form name, count…; never answers);
 * `link` is an in-app path; `only` limits it to these members (an export goes to whoever asked).
 */
export function notify(event: H3Event | null, tenant: MockTenant, type: NotificationEvent, params: Record<string, string | number>, link: string | null, options: { only?: string[] } = {}) {
  try {
    const { notifications } = settingsOf(tenant)
    const rule = notifications.events[type]
    if (!rule.in_app && !rule.email) return
    const store = notificationsOf(tenant)
    const { members, emails } = recipients(tenant, rule, options.only)
    const at = new Date().toISOString()
    if (rule.in_app) for (const user_id of members) store.items.unshift({ id: crypto.randomUUID(), user_id, event: type, params, link, created_at: at, read_at: null })
    store.items = store.items.slice(0, KEEP * 20)
    if (rule.email && emails.length) {
      const language = emailLanguage(tenant)
      const texts = emailDefaults(language)
      const vars = { workspace: settingsOf(tenant).company.display_name || tenant.name, ...params, reason: params.reason ? (texts.reasons[String(params.reason)] ?? String(params.reason)) : '' }
      const title = fillIn(texts.events[type]!.title, vars)
      for (const person of emails) {
        if (notifications.digest.enabled) {
          const entry = (store.digest[person.email] ??= { name: person.name, lines: [] })
          entry.lines.push(title)
        } else sendEmail(tenant, { to: person.email, key: 'notification', vars: { title, message: fillIn(texts.events[type]!.message, vars), link: workspaceUrl(event, tenant, link ?? '/') }, reason: type })
      }
    }
    save()
  } catch (error) {
    console.error('[notifications]', error)
  }
}

/** Sends the waiting daily summaries once the hour has come (or now, `force`); returns how many went out. */
export function flushDigest(event: H3Event | null, tenant: MockTenant, force = false): number {
  const { digest } = settingsOf(tenant).notifications
  const store = notificationsOf(tenant)
  const today = new Date().toISOString().slice(0, 10)
  if (!force && (!digest.enabled || store.digest_sent_on === today || new Date().getUTCHours() < digest.hour)) return 0
  const texts = emailDefaults(emailLanguage(tenant))
  let sent = 0
  for (const [email, entry] of Object.entries(store.digest)) {
    if (!entry.lines.length) continue
    const counts = new Map<string, number>()
    for (const line of entry.lines) counts.set(line, (counts.get(line) ?? 0) + 1)
    const summary = [...counts].map(([title, count]) => (count > 1 ? fillIn(texts.layout.summary, { count, title }) : title)).join('\n')
    if (sendEmail(tenant, { to: email, key: 'daily_digest', vars: { name: entry.name, summary, link: workspaceUrl(event, tenant, '/') }, reason: 'daily_digest' })) sent++
  }
  store.digest = {}
  store.digest_sent_on = today
  save()
  return sent
}

/** Something announced only once (a form closing at a given time, a finished export). */
export function announceOnce(tenant: MockTenant, key: string): boolean {
  const store = notificationsOf(tenant)
  if (store.announced.includes(key)) return false
  store.announced = [key, ...store.announced].slice(0, 2000)
  save()
  return true
}

export function feedOf(tenant: MockTenant, userId: string) {
  const mine = notificationsOf(tenant).items.filter(item => item.user_id === userId)
  return { items: mine.slice(0, KEEP).map(({ user_id: _u, ...item }) => item), unread: mine.filter(item => !item.read_at).length }
}

export function markRead(tenant: MockTenant, userId: string, ids: string[] | 'all') {
  const at = new Date().toISOString()
  for (const item of notificationsOf(tenant).items) if (item.user_id === userId && !item.read_at && (ids === 'all' || ids.includes(item.id))) item.read_at = at
  save()
}

export function clearRead(tenant: MockTenant, userId: string) {
  const store = notificationsOf(tenant)
  store.items = store.items.filter(item => item.user_id !== userId || !item.read_at)
  save()
}

/** A new response (form page or API): "new response", a possible duplicate, and the limit when it was the last one. */
export function notifyResponse(event: H3Event | null, tenant: MockTenant, form: { id: string; name: string; response_limit?: number | null; responses_count: number }, responseId: string, duplicate: boolean) {
  const link = `/forms/${encodeId(form.id)}/responses?response=${encodeId(responseId)}`
  notify(event, tenant, duplicate ? 'response_duplicate' : 'response_new', { form: form.name }, link)
  if (form.response_limit != null && form.responses_count === form.response_limit) notify(event, tenant, 'form_limit', { form: form.name, limit: form.response_limit }, `/forms/${encodeId(form.id)}/share`)
}
