/**
 * People of a workspace in the mock (F16 Users & profiles), kept in `.data/mock/people.json`: what the
 * workspace knows about each person besides their sign-in account (role, status, manager, joined date,
 * two-step sign-in). Departments and job titles stay in the organisation data (orgStore, Settings), so
 * both pages always agree; sign-ins and activity come from the audit trail. The demo workspaces start
 * with their sign-in accounts and the sample colleagues who own their forms.
 */
import type { WorkspaceRole } from '#shared/types/auth'
import type { DateFormat } from '#shared/types/onboarding'
import type { PersonDetail, PersonRow, PersonStatus } from '#shared/types/people'
import { auditLogOf } from '../core/audit'
import { latestSessions, whenRecoveryUsed } from '../core/auth'
import { loadPersisted, savePersisted } from '../core/persist'
import { MOCK_OWNERS } from './forms'
import { formsOf } from './formStore'
import { orgOf } from './orgStore'
import { MOCK_PASSWORD, MOCK_USERS, type MockTenant } from './tenants'
import { roleOf } from './rolesStore'

export interface StoredPerson {
  id: string
  first_name: string
  last_name: string
  email: string
  phone: string | null
  role: WorkspaceRole
  status: PersonStatus
  manager_id: string | null
  two_step: boolean
  joined_at: string
  /** An admin asked for a new password at the next sign-in (F16 M3). */
  must_change_password?: boolean
  /** A password changed in My profile, as a hash (the demo's built-in accounts aren't saved elsewhere). */
  password_hash?: string
  /** My profile (F16 M5), kept here so the demo's built-in accounts keep them across restarts. */
  totp_secret?: string | null
  recovery_hashes?: string[]
  photo?: string | null
  language?: string | null
  time_zone?: string | null
  date_format?: DateFormat | null
  notifications?: Record<string, boolean>
  /** Tips on new pages (first-visit tours): switched off, and the tours already offered (shown or skipped). */
  tours?: { off?: boolean; seen: string[] }
  /** An open invitation (F16 M2): only a hash of the link's token is kept. */
  invite?: { kind?: 'invite' | 'activation'; token_hash: string; expires_at: string; sent_at: string; invited_by: { id: string; name: string }; message: string | null }
  /** Signed up with a link, waiting for approval (R3 / R4). */
  request?: { via: 'invite' | 'link'; at: string }
}

const stores = new Map<string, StoredPerson[]>(Object.entries(loadPersisted<Record<string, StoredPerson[]>>('people', {})))
export const savePeople = () => savePersisted('people', () => Object.fromEntries(stores))

/** Puts role, status and a password request back on the sign-in accounts (the demo's built-in ones aren't saved to disk). */
function syncAccounts(tenantId: string, list: StoredPerson[]) {
  for (const person of list) {
    // Everyone who has signed in or is waiting for approval has an account. Sample colleagues and people who
    // joined in an earlier run get one here (mock only: their own password if they set one, else the test password)
    if (['active', 'disabled', 'pending'].includes(person.status) && !MOCK_USERS.some(item => item.id === person.id && item.tenant_id === tenantId))
      MOCK_USERS.push({ id: person.id, tenant_id: tenantId, first_name: person.first_name, last_name: person.last_name, email: person.email, password: person.password_hash ?? MOCK_PASSWORD, phone: person.phone ?? null, disabled: false, role: person.role, awaiting_approval: person.status === 'pending' })
    const user = MOCK_USERS.find(item => item.id === person.id && item.tenant_id === tenantId)
    if (user && person.status !== 'invited' && person.status !== 'not_activated')
      Object.assign(user, {
        role: person.role,
        disabled: person.status === 'disabled',
        must_change_password: !!person.must_change_password,
        totp_secret: person.totp_secret ?? null,
        recovery_hashes: person.recovery_hashes ?? [],
        photo: person.photo ?? null,
        language: person.language ?? null,
        time_zone: person.time_zone ?? null,
        date_format: person.date_format ?? null,
        ...(person.phone !== undefined ? { phone: person.phone } : {}),
        ...(person.password_hash ? { password: person.password_hash } : {}),
      })
  }
}
// At start, before anyone signs in, so access follows what admins set (F16 M3)
for (const [tenantId, list] of stores) syncAccounts(tenantId, list)
// A recovery code used at sign-in is crossed off here too (F16 M5)
whenRecoveryUsed(user => {
  for (const list of stores.values()) {
    const person = list.find(item => item.id === user.id)
    if (person) person.recovery_hashes = user.recovery_hashes ?? []
  }
  savePeople()
})

const DAY = 86_400_000

function seed(tenant: MockTenant): StoredPerson[] {
  const users = MOCK_USERS.filter(user => user.tenant_id === tenant.id)
  const fromUsers: StoredPerson[] = users.map((user, i) => ({
    id: user.id,
    first_name: user.first_name,
    last_name: user.last_name,
    email: user.email,
    phone: user.phone,
    role: user.role,
    status: user.disabled ? 'disabled' : 'active',
    manager_id: null,
    two_step: !!user.phone,
    joined_at: new Date(Date.now() - (400 - i * 37) * DAY).toISOString(),
  }))
  // Sample colleagues (they own the demo forms) only in workspaces that have demo forms
  const owner = users.find(user => user.role === 'owner')
  const samples: StoredPerson[] = owner && formsOf(tenant).forms.some(form => MOCK_OWNERS.some(item => item.id === form.owner?.id))
    ? MOCK_OWNERS.map((colleague, i) => {
        const [first = colleague.name, ...rest] = colleague.name.split(' ')
        return {
          id: colleague.id,
          first_name: first,
          last_name: rest.join(' '),
          email: `${colleague.name.toLowerCase().replace(/\s+/g, '.')}@${tenant.subdomain}.test`,
          phone: null,
          role: i === 0 ? 'admin' : 'member',
          status: 'active',
          manager_id: i === 0 ? owner.id : MOCK_OWNERS[0]!.id,
          two_step: i % 2 === 0,
          joined_at: new Date(Date.now() - (300 - i * 45) * DAY).toISOString(),
        } satisfies StoredPerson
      })
    : []
  return [...fromUsers, ...samples]
}

const synced = new Set<string>()
export function peopleStoreOf(tenant: MockTenant): StoredPerson[] {
  let list = stores.get(tenant.id)
  if (!list) {
    list = seed(tenant)
    stores.set(tenant.id, list)
    savePeople()
  }
  // A store seeded just now: the same, once
  if (!synced.has(tenant.id)) {
    synced.add(tenant.id)
    syncAccounts(tenant.id, list)
  }
  return list
}
/** The person and their sign-in account (sample colleagues have none). */
export const accountOf = (id: string) => MOCK_USERS.find(user => user.id === id) ?? null

const refOf = (item: { id: string; name: string }) => ({ id: item.id, name: item.name })

/** The People page's rows, with departments and job titles from the organisation data and activity from the audit trail. */
export function peopleRows(tenant: MockTenant): PersonRow[] {
  const people = peopleStoreOf(tenant)
  const org = orgOf(tenant)
  const lastSeen = new Map<string, string>()
  // The latest visit from the audit trail (newest first): a run of actions with gaps under 30 minutes
  const visits = new Map<string, { start: number; end: number; done: boolean }>()
  for (const event of auditLogOf(tenant)) {
    const id = event.actor.id
    if (!id || event.outcome === 'blocked' || event.outcome === 'failure') continue
    const at = Date.parse(event.occurred_at)
    if (!lastSeen.has(id)) lastSeen.set(id, event.occurred_at)
    const visit = visits.get(id)
    if (!visit) visits.set(id, { start: at, end: at, done: false })
    else if (!visit.done) {
      if (visit.start - at < 30 * 60_000) visit.start = at
      else visit.done = true
    }
  }
  const sessions = latestSessions(tenant)
  const visitOf = (id: string): PersonRow['last_visit'] => {
    const session = sessions.get(id)
    const trail = visits.get(id)
    if (session && (!trail || session.lastActiveAt >= trail.end)) return { started_at: new Date(session.startedAt).toISOString(), ended_at: new Date(Math.max(session.lastActiveAt, trail?.end ?? 0)).toISOString(), online: session.open && Date.now() - session.lastActiveAt < 5 * 60_000 }
    return trail ? { started_at: new Date(trail.start).toISOString(), ended_at: new Date(trail.end).toISOString(), online: false } : null
  }
  // Like the forms list: archived and deleted forms aren't counted
  const forms = formsOf(tenant).forms.filter(form => !form.deleted_at && form.status !== 'archived')
  const nameOf = (person: StoredPerson) => `${person.first_name} ${person.last_name}`.trim() || person.email
  return people.map(person => {
    const manager = person.manager_id ? people.find(item => item.id === person.manager_id) : undefined
    // Never signed in yet (invited, not activated, awaiting approval)
    const away = ['invited', 'not_activated', 'pending'].includes(person.status)
    const visit = away ? null : visitOf(person.id)
    return {
      id: person.id,
      first_name: person.first_name,
      last_name: person.last_name,
      name: nameOf(person),
      email: person.email,
      phone: person.phone,
      photo: person.photo ?? null,
      role: person.role,
      role_name: roleOf(tenant, person.role)?.name ?? person.role,
      privileged: person.role === 'owner' || ['people.manage', 'settings.manage', 'roles.manage'].some(item => roleOf(tenant, person.role)?.grants[item as never]),
      status: person.status,
      departments: org.departments.filter(item => !item.archived_at && item.member_ids.includes(person.id)).map(refOf),
      job_titles: org.job_titles.filter(item => !item.archived_at && item.member_ids.includes(person.id)).map(refOf),
      manager: manager ? { id: manager.id, name: nameOf(manager) } : null,
      two_step: person.two_step,
      last_active_at: away ? null : (visit?.ended_at ?? lastSeen.get(person.id) ?? null),
      last_visit: away ? null : visit,
      joined_at: person.joined_at,
      forms_count: forms.filter(form => form.owner?.id === person.id).length,
      request: person.request ?? null,
      invite: person.invite ? { kind: person.invite.kind ?? 'invite', expires_at: person.invite.expires_at, sent_at: person.invite.sent_at, invited_by: person.invite.invited_by.name, expired: Date.parse(person.invite.expires_at) < Date.now() } : null,
    }
  })
}

/** One person's detail: their row, last sign-in, 30-day activity and who reports to them. */
export function personDetail(tenant: MockTenant, id: string): PersonDetail | null {
  const rows = peopleRows(tenant)
  const row = rows.find(item => item.id === id)
  if (!row) return null
  const since = Date.now() - 30 * DAY
  const mine = auditLogOf(tenant).filter(event => event.actor.id === id)
  const signIn = mine.find(event => event.action === 'auth.login.succeeded')
  const recent = mine.filter(event => Date.parse(event.occurred_at) >= since)
  return {
    ...row,
    last_sign_in: signIn ? { at: signIn.occurred_at, city: signIn.location.city, country: signIn.location.country, browser: signIn.device.browser, os: signIn.device.os } : null,
    sign_ins_30d: recent.filter(event => event.action === 'auth.login.succeeded').length,
    actions_30d: recent.length,
    reports: rows.filter(item => item.manager?.id === id).map(item => ({ id: item.id, name: item.name })),
    // Their forms, most recently changed first (the forms list filters by owner for the rest)
    forms: formsOf(tenant)
      .forms.filter(form => !form.deleted_at && form.status !== 'archived' && form.owner?.id === id)
      .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
      .slice(0, 5)
      .map(form => ({ id: form.id, name: form.name, status: form.status })),
  }
}
