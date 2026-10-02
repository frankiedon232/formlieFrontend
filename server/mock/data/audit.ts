/**
 * Seeded audit history per workspace (deterministic per workspace, times relative to server
 * start so the trail looks live). International team, offices and devices — no single country.
 * IPs come from the reserved documentation ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24).
 */
import type { AuditActor, AuditChange, AuditDevice, AuditEvent, AuditLocation } from '#shared/types/audit'
import { AUDIT_EVENTS, type AuditAction } from '#shared/utils/audit/events'
import { MOCK_FORMS, MOCK_OWNERS } from './forms'
import { MOCK_USERS, type MockTenant } from './tenants'

function seeded(seed: number) {
  let state = seed
  return () => {
    state = (state * 1_103_515_245 + 12_345) % 2_147_483_648
    return state / 2_147_483_648
  }
}

const OFFICES: AuditLocation[] = [
  { ip: '198.51.100.24', city: 'London', country: 'GB' },
  { ip: '203.0.113.41', city: 'Lisbon', country: 'PT' },
  { ip: '192.0.2.77', city: 'Tokyo', country: 'JP' },
  { ip: '198.51.100.130', city: 'Bengaluru', country: 'IN' },
  { ip: '203.0.113.9', city: 'Prague', country: 'CZ' },
  { ip: '192.0.2.150', city: 'Berlin', country: 'DE' },
  { ip: '198.51.100.66', city: 'Toronto', country: 'CA' },
]

/** Where unexpected sign-in attempts come from. */
const UNUSUAL: AuditLocation[] = [
  { ip: '203.0.113.188', city: 'São Paulo', country: 'BR' },
  { ip: '192.0.2.201', city: 'Singapore', country: 'SG' },
  { ip: '198.51.100.210', city: 'Sydney', country: 'AU' },
  { ip: '203.0.113.240', city: 'Mexico City', country: 'MX' },
  { ip: '192.0.2.33', city: 'Dubai', country: 'AE' },
]

const DEVICES: AuditDevice[] = [
  { type: 'desktop', browser: 'Chrome', os: 'Windows' },
  { type: 'desktop', browser: 'Safari', os: 'macOS' },
  { type: 'desktop', browser: 'Edge', os: 'Windows' },
  { type: 'desktop', browser: 'Firefox', os: 'Linux' },
  { type: 'mobile', browser: 'Safari', os: 'iOS' },
  { type: 'mobile', browser: 'Chrome', os: 'Android' },
  { type: 'tablet', browser: 'Safari', os: 'iOS' },
]

interface Person {
  actor: AuditActor
  home: AuditLocation
  device: AuditDevice
  mobile: AuditDevice
}

const DAY = 86_400_000
const HISTORY_DAYS = 90
const startedAt = Date.now()

export function seedAuditHistory(tenant: MockTenant): AuditEvent[] {
  const users = MOCK_USERS.filter(user => user.tenant_id === tenant.id)
  // Only the seeded workspaces get history; a new workspace starts with its own real events.
  if (!users.length || users.every(user => user.role !== 'owner')) return []
  if (tenant.status !== 'active') return []

  const random = seeded([...tenant.id].reduce((sum, char) => sum + char.charCodeAt(0), 0) * 7919)
  const pick = <T>(items: readonly T[]): T => items[Math.floor(random() * items.length)]!
  const uuid = () => {
    const hex = () => Math.floor(random() * 16).toString(16)
    const part = (n: number) => Array.from({ length: n }, hex).join('')
    return `${part(8)}-${part(4)}-4${part(3)}-a${part(3)}-${part(12)}`
  }

  const domain = `${tenant.subdomain}.test`
  const person = (actor: AuditActor, index: number): Person => ({
    actor,
    home: OFFICES[index % OFFICES.length]!,
    device: DEVICES[index % 4]!,
    mobile: DEVICES[4 + (index % 3)]!,
  })
  const owner = users.find(user => user.role === 'owner')!
  const people: Person[] = [
    ...users
      .filter(user => !user.disabled)
      .map(user => ({
        type: 'user' as const,
        id: user.id,
        name: `${user.first_name} ${user.last_name}`,
        email: user.email,
      })),
    ...MOCK_OWNERS.map(colleague => ({
      type: 'user' as const,
      id: colleague.id,
      name: colleague.name,
      email: `${colleague.name.toLowerCase().replace(/\s+/g, '.')}@${domain}`,
    })),
  ].map(person)
  const ownerPerson = people.find(p => p.actor.id === owner.id)!
  const disabled = users.find(user => user.disabled)

  const events: AuditEvent[] = []
  const add = (
    at: number,
    who: Person,
    action: AuditAction,
    extra: Partial<Omit<AuditEvent, 'id' | 'action' | 'area'>> = {},
  ) => {
    const outcome = extra.outcome ?? 'success'
    events.push({
      id: uuid(),
      occurred_at: new Date(at).toISOString(),
      action,
      area: AUDIT_EVENTS[action].area,
      outcome,
      severity:
        extra.severity ?? (outcome === 'success' ? 'info' : outcome === 'failure' ? 'warning' : 'critical'),
      actor: extra.actor ?? who.actor,
      resource: extra.resource ?? null,
      organisation: tenant.organisation,
      location: extra.location ?? who.home,
      device: extra.device ?? (random() < 0.2 ? who.mobile : who.device),
      changes: extra.changes ?? [],
      metadata: extra.metadata ?? {},
      reason: extra.reason ?? null,
      request_id: uuid(),
    })
  }
  const change = (field: string, before: AuditChange['before'], after: AuditChange['after']) => [
    { field, before, after },
  ]
  const formRef = () => {
    const form = pick(MOCK_FORMS)
    return { form, resource: { type: 'form', id: form.id, name: form.name } }
  }

  // ── The workspace story: created, team invited, storage connected ────────────────
  const start = startedAt - HISTORY_DAYS * DAY
  add(start, ownerPerson, 'workspace.created', {
    resource: { type: 'workspace', id: tenant.id, name: tenant.name },
    metadata: { subdomain: tenant.subdomain },
  })
  people.slice(1).forEach((p, index) =>
    add(start + (index + 1) * 3_600_000, ownerPerson, 'users.invited', {
      resource: { type: 'user', id: p.actor.id, name: p.actor.name },
      metadata: { role: index === 0 ? 'admin' : 'member' },
    }),
  )
  add(start + DAY, ownerPerson, 'settings.updated', {
    resource: { type: 'setting', id: null, name: 'Branding' },
    changes: change('brand_colour', '#18181B', '#0F766E'),
  })
  add(start + 2 * DAY, ownerPerson, 'integrations.destination_connected', {
    resource: { type: 'destination', id: uuid(), name: 'Customer records (PostgreSQL)' },
    metadata: { engine: 'PostgreSQL', host: 'db.internal.example' },
  })
  add(start + 3 * DAY, ownerPerson, 'integrations.api_key_created', {
    resource: { type: 'api_key', id: uuid(), name: 'Reporting export' },
    metadata: { scopes: 'responses:read', expires: '90 days' },
  })
  add(start + 9 * DAY, ownerPerson, 'settings.updated', {
    resource: { type: 'setting', id: null, name: 'Security' },
    changes: change('session_timeout_minutes', 30, 60),
  })
  add(start + 12 * DAY, ownerPerson, 'settings.updated', {
    resource: { type: 'setting', id: null, name: 'Authentication' },
    changes: change('sign_in_methods', 'Email + password', 'Email + password, Google'),
  })
  if (people[1])
    add(start + 20 * DAY, ownerPerson, 'users.role_changed', {
      resource: { type: 'user', id: people[1].actor.id, name: people[1].actor.name },
      changes: change('role', 'member', 'admin'),
    })
  if (disabled) {
    const marcus = person(
      {
        type: 'user',
        id: disabled.id,
        name: `${disabled.first_name} ${disabled.last_name}`,
        email: disabled.email,
      },
      5,
    )
    add(start + 30 * DAY, ownerPerson, 'users.disabled', {
      resource: { type: 'user', id: disabled.id, name: marcus.actor.name },
      changes: change('status', 'active', 'disabled'),
      metadata: { note: 'Left the company' },
    })
    add(start + 31 * DAY, marcus, 'auth.login.blocked', {
      outcome: 'blocked',
      severity: 'notice',
      reason: 'FRM-AUTH-1005',
      metadata: { method: 'password' },
    })
  }
  add(start + 40 * DAY, ownerPerson, 'integrations.webhook_created', {
    resource: { type: 'webhook', id: uuid(), name: 'https://hooks.example.com/formalie' },
    metadata: { events: 'response.created' },
  })

  // ── Day-to-day activity ─────────────────────────────────────────────────────────
  for (let day = HISTORY_DAYS - 1; day >= 0; day--) {
    const dayStart = startedAt - day * DAY - DAY
    const weekend = new Date(dayStart).getUTCDay() % 6 === 0
    const count = weekend ? Math.floor(random() * 3) : 3 + Math.floor(random() * 6)
    for (let n = 0; n < count; n++) {
      const who = pick(people)
      const at = Math.min(startedAt - 60_000, dayStart + Math.floor(random() * DAY))
      const roll = random()
      if (roll < 0.3) {
        const method = random() < 0.75 ? 'password' : 'google'
        if (method === 'password')
          add(at - 40_000, who, 'auth.otp.sent', { metadata: { channel: random() < 0.85 ? 'email' : 'sms' } })
        add(at, who, 'auth.login.succeeded', { metadata: { method } })
      } else if (roll < 0.38) {
        add(at, who, 'auth.logout')
      } else if (roll < 0.43) {
        add(at, who, 'auth.login.failed', {
          outcome: 'failure',
          reason: 'FRM-AUTH-1002',
          metadata: { method: 'password' },
        })
      } else if (roll < 0.46) {
        add(at, who, 'auth.otp.failed', {
          outcome: 'failure',
          reason: 'FRM-AUTH-1003',
          metadata: { channel: 'email', attempts_left: String(1 + Math.floor(random() * 4)) },
        })
      } else if (roll < 0.62) {
        const { form, resource } = formRef()
        add(at, who, 'forms.updated', {
          resource,
          changes: random() < 0.5 ? change('name', `${form.name} (draft)`, form.name) : [],
          metadata: { version: String(2 + Math.floor(random() * 8)) },
        })
      } else if (roll < 0.68) {
        add(at, who, 'forms.created', {
          resource: formRef().resource,
          metadata: { source: random() < 0.5 ? 'template' : 'blank' },
        })
      } else if (roll < 0.74) {
        add(at, who, 'forms.published', {
          resource: formRef().resource,
          changes: change('status', 'draft', 'published'),
        })
      } else if (roll < 0.77) {
        add(at, who, 'forms.closed', {
          resource: formRef().resource,
          changes: change('status', 'published', 'closed'),
        })
      } else if (roll < 0.8) {
        add(at, who, 'forms.archived', {
          resource: formRef().resource,
          changes: change('status', 'closed', 'archived'),
        })
      } else if (roll < 0.82) {
        add(at, who, 'forms.shared', {
          resource: formRef().resource,
          metadata: { with: pick(people).actor.name, access: random() < 0.5 ? 'edit' : 'view' },
        })
      } else if (roll < 0.9) {
        add(at, who, 'responses.updated', {
          resource: { type: 'response', id: uuid(), name: formRef().form.name },
          changes: change('response_status', 'new', random() < 0.7 ? 'reviewed' : 'approved'),
        })
      } else if (roll < 0.96) {
        add(at, who, 'responses.exported', {
          resource: { type: 'form', id: null, name: formRef().form.name },
          metadata: {
            format: random() < 0.7 ? 'xlsx' : 'csv',
            rows: String(50 + Math.floor(random() * 2000)),
          },
        })
      } else if (roll < 0.98) {
        const { resource } = formRef()
        add(at, who, 'forms.deleted', { resource, metadata: { kept_in_trash: '30 days' } })
        add(at + 3_600_000, who, 'forms.restored', { resource })
      } else {
        add(at, who, 'audit.exported', {
          metadata: { format: 'xlsx', rows: String(100 + Math.floor(random() * 900)) },
        })
      }
    }
  }

  // ── A few security moments ──────────────────────────────────────────────────────
  const target = pick(people)
  for (let attempt = 0; attempt < 4; attempt++) {
    add(startedAt - 6 * DAY + attempt * 45_000, target, 'auth.login.failed', {
      outcome: 'failure',
      reason: 'FRM-AUTH-1002',
      location: UNUSUAL[0],
      device: { type: 'desktop', browser: null, os: 'Linux' },
      metadata: { method: 'password' },
    })
  }
  add(startedAt - 6 * DAY + 4 * 45_000, target, 'auth.otp.locked', {
    outcome: 'blocked',
    reason: 'FRM-AUTH-1004',
    location: UNUSUAL[0],
    device: { type: 'desktop', browser: null, os: 'Linux' },
  })
  add(startedAt - 2 * DAY, ownerPerson, 'auth.session.revoked', {
    outcome: 'blocked',
    reason: 'FRM-AUTH-1012',
    location: UNUSUAL[1],
    metadata: { cause: 'refresh_token_reuse' },
  })
  add(startedAt - 3 * 3_600_000, ownerPerson, 'auth.login.failed', {
    outcome: 'failure',
    reason: 'FRM-AUTH-1002',
    actor: { type: 'user', id: null, name: `it-support@${domain}`, email: `it-support@${domain}` },
    location: pick(UNUSUAL.slice(2)),
    device: { type: 'unknown', browser: null, os: null },
  })
  add(startedAt - 20 * 60_000, ownerPerson, 'auth.password.reset_requested', {
    metadata: { channel: 'email' },
  })
  add(startedAt - 17 * 60_000, ownerPerson, 'auth.password.reset')

  return events.sort((a, b) => b.occurred_at.localeCompare(a.occurred_at))
}
