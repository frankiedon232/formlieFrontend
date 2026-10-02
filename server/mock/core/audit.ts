/**
 * Mock audit trail: one in-memory list per workspace. `recordAudit()` is called by every
 * mock route that changes something or signs someone in / out (PROGRESS.md → F4), with the
 * request's IP, device and request id filled in here. Seeded history: ../data/audit.ts.
 */
import type { H3Event } from 'h3'
import type { AuditActor, AuditDevice, AuditEvent, AuditOutcome, AuditSeverity } from '#shared/types/audit'
import { AUDIT_EVENTS, type AuditAction } from '#shared/utils/audit/events'
import { seedAuditHistory } from '../data/audit'
import type { MockTenant, MockUser } from '../data/tenants'

const logs = new Map<string, AuditEvent[]>()

/** The workspace's events, newest first (seeded on first use). */
export function auditLogOf(tenant: MockTenant): AuditEvent[] {
  let list = logs.get(tenant.id)
  if (!list) {
    list = seedAuditHistory(tenant)
    logs.set(tenant.id, list)
  }
  return list
}

export function deviceFrom(userAgent: string): AuditDevice {
  const ua = userAgent
  const browser = /Edg\//.test(ua)
    ? 'Edge'
    : /OPR\//.test(ua)
      ? 'Opera'
      : /Firefox\//.test(ua)
        ? 'Firefox'
        : /Chrome\//.test(ua)
          ? 'Chrome'
          : /Safari\//.test(ua)
            ? 'Safari'
            : null
  const os = /iPhone|iPad|iPod/.test(ua)
    ? 'iOS'
    : /Android/.test(ua)
      ? 'Android'
      : /Windows/.test(ua)
        ? 'Windows'
        : /Mac OS X/.test(ua)
          ? 'macOS'
          : /Linux/.test(ua)
            ? 'Linux'
            : null
  const type = /iPad|Tablet/.test(ua) ? 'tablet' : /Mobi|iPhone|Android/.test(ua) ? 'mobile' : 'desktop'
  return { type: ua ? type : 'unknown', browser, os }
}

export const actorOf = (user: MockUser): AuditActor => ({
  type: 'user',
  id: user.id,
  name: `${user.first_name} ${user.last_name}`.trim(),
  email: user.email,
})

/** Someone who is not (yet) signed in, known only by the email they typed. */
export const anonymousActor = (email: string): AuditActor => ({
  type: 'user',
  id: null,
  name: email,
  email,
})

const DEFAULT_SEVERITY: Record<AuditOutcome, AuditSeverity> = {
  success: 'info',
  failure: 'warning',
  blocked: 'critical',
}

export interface AuditInput {
  action: AuditAction
  actor: AuditActor
  outcome?: AuditOutcome
  severity?: AuditSeverity
  resource?: AuditEvent['resource']
  changes?: AuditEvent['changes']
  metadata?: Record<string, string>
  reason?: string | null
}

export function recordAudit(event: H3Event, tenant: MockTenant, input: AuditInput): AuditEvent {
  const outcome = input.outcome ?? 'success'
  const entry: AuditEvent = {
    id: crypto.randomUUID(),
    occurred_at: new Date().toISOString(),
    action: input.action,
    area: AUDIT_EVENTS[input.action].area,
    outcome,
    severity: input.severity ?? DEFAULT_SEVERITY[outcome],
    actor: input.actor,
    resource: input.resource ?? null,
    organisation: tenant.organisation,
    // A real backend resolves city / country from the IP (GeoIP); local addresses stay unknown.
    location: { ip: getRequestIP(event, { xForwardedFor: true }) ?? 'unknown', city: null, country: null },
    device: deviceFrom(getHeader(event, 'user-agent') ?? ''),
    changes: input.changes ?? [],
    metadata: input.metadata ?? {},
    reason: input.reason ?? null,
    request_id: (event.context.requestId as string | undefined) ?? crypto.randomUUID(),
  }
  auditLogOf(tenant).unshift(entry)
  return entry
}
