/**
 * Where emails come from (Settings → Emails → Sending address, owner 2026-10-10; docs/API-CONTRACT.md → Emails).
 * Admins only.
 *
 *   GET    /settings/emails/sending                  mode, the address used now, own domain, own mail server
 *   PUT    /settings/emails/sending/domain           { address } → the DNS records to add (SPF, two DKIM, bounces, DMARC)
 *   POST   /settings/emails/sending/domain/check     looks the records up in DNS (really) → status
 *   DELETE /settings/emails/sending/domain
 *   PUT    /settings/emails/sending/smtp             SmtpSaveRequest (password write-only)
 *   POST   /settings/emails/sending/smtp/test        connects to the server (really) and reads its greeting
 *   DELETE /settings/emails/sending/smtp
 *   POST   /settings/emails/sending/mode             { mode } (domain: verified first; smtp: working first, else FRM-SET-1001)
 *
 * Formalie's mark stays under every email whatever the address (owner, 2026-10-07). Every change is audited.
 */
import { resolveCname, resolveTxt } from 'node:dns/promises'
import { connect as connectTcp } from 'node:net'
import { connect as connectTls } from 'node:tls'
import type { H3Event } from 'h3'
import { z } from 'zod'
import type { DnsRecord, EmailSending, SendingDomain, SmtpServer } from '#shared/types/emails'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { FORMALIE_ADDRESS, fromAddress, sendingOf, updateSending } from '../data/sendingStore'
import type { MockTenant, MockUser } from '../data/tenants'

function view(tenant: MockTenant): EmailSending {
  const sending = sendingOf(tenant)
  const smtp = sending.smtp ? (({ password: _p, ...rest }) => rest)(sending.smtp) : null
  return { mode: sending.mode, from_address: fromAddress(tenant), formalie_address: FORMALIE_ADDRESS, domain: sending.domain, smtp }
}
const audit = (event: H3Event, tenant: MockTenant, user: MockUser, field: string, before: string | null, after: string | null) =>
  recordAudit(event, tenant, { action: 'settings.updated', actor: actorOf(user), resource: { type: 'setting', id: null, name: 'Sending address' }, changes: [{ field, before, after }] })

export const getSending = defineMockRoute(({ event }) => ok(view(requireAdmin(event).tenant)))

// Own address on the workspace's domain
const addressSchema = z.object({ address: z.string().trim().toLowerCase().max(200).pipe(z.email()) })
const blocked = (domain: string, root: string) => domain === root || domain.endsWith(`.${root}`) || domain === 'formalie.com' || domain.endsWith('.formalie.com')

export const addSendingDomain = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const { address } = parseBody(addressSchema, body)
  const domain = address.split('@').pop()!
  if (blocked(domain, useRuntimeConfig(event).public.rootDomain)) throw new MockError('FRM-GEN-1002', [{ field: 'address', message: 'domain' }])
  const key = crypto.randomUUID().replace(/-/g, '').slice(0, 12)
  const records: DnsRecord[] = [
    { type: 'TXT', name: domain, value: 'v=spf1 include:spf.formalie.com ~all', found: false },
    { type: 'CNAME', name: `fm1._domainkey.${domain}`, value: `fm1.${key}.dkim.formalie.com`, found: false },
    { type: 'CNAME', name: `fm2._domainkey.${domain}`, value: `fm2.${key}.dkim.formalie.com`, found: false },
    { type: 'CNAME', name: `fm-bounces.${domain}`, value: 'bounces.formalie.com', found: false },
    { type: 'TXT', name: `_dmarc.${domain}`, value: `v=DMARC1; p=none; rua=mailto:dmarc@${domain}`, found: false, optional: true },
  ]
  const before = sendingOf(tenant).domain?.address ?? null
  updateSending(tenant, sending => (sending.domain = { address, domain, status: 'pending', records, added_at: new Date().toISOString(), checked_at: null, problem: null }))
  audit(event, tenant, user, 'sending_domain', before, address)
  return ok(view(tenant))
})

/** A DNS lookup that gives up after a few seconds; "no such record" is an empty answer, not an error. */
const lookup = <T>(work: Promise<T[]>) =>
  Promise.race([work, new Promise<never>((_, reject) => setTimeout(() => reject(new Error('timeout')), 4000))]).catch(error =>
    ['ENODATA', 'ENOTFOUND'].includes((error as { code?: string }).code ?? '') ? ([] as T[]) : Promise.reject(error),
  )
const clean = (value: string) => value.replace(/\.$/, '').toLowerCase()

export const checkSendingDomain = defineMockRoute(async ({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const entry = sendingOf(tenant).domain
  if (!entry) throw new MockError('FRM-GEN-1004')
  let problem: SendingDomain['problem'] = null
  let wrong = false
  try {
    for (const record of entry.records) {
      if (record.type === 'CNAME') {
        const targets = await lookup(resolveCname(record.name))
        record.found = targets.some(target => clean(target) === record.value)
        wrong ||= !!targets.length && !record.found
      } else {
        const texts = (await lookup(resolveTxt(record.name))).map(parts => parts.join(''))
        // SPF: any SPF record that includes Formalie's (people merge it into the one they have)
        record.found = record.value.startsWith('v=spf1') ? texts.some(text => text.startsWith('v=spf1') && text.includes('include:spf.formalie.com')) : record.value.startsWith('v=DMARC1') ? texts.some(text => text.startsWith('v=DMARC1')) : texts.includes(record.value)
        wrong ||= record.value.startsWith('v=spf1') && texts.some(text => text.startsWith('v=spf1')) && !record.found
      }
    }
    const missing = entry.records.filter(record => !record.optional && !record.found)
    problem = missing.length ? (wrong ? 'wrong_value' : 'not_found') : null
  } catch {
    problem = 'dns_error'
  }
  const before = entry.status
  updateSending(tenant, () => {
    entry.status = problem ? (problem === 'wrong_value' ? 'failed' : 'pending') : 'verified'
    entry.problem = problem
    entry.checked_at = new Date().toISOString()
  })
  if (before !== entry.status) audit(event, tenant, user, 'sending_domain_status', before, entry.status)
  return ok(view(tenant))
})

export const removeSendingDomain = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const entry = sendingOf(tenant).domain
  if (entry) {
    updateSending(tenant, sending => (sending.domain = null))
    audit(event, tenant, user, 'sending_domain', entry.address, null)
  }
  return ok(view(tenant))
})

// Own mail server
const HOST = /^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/
const smtpSchema = z.object({
  host: z.string().trim().toLowerCase().max(253).refine(value => HOST.test(value), 'host'),
  port: z.number().int().min(1).max(65535),
  security: z.enum(['starttls', 'tls', 'none']),
  username: z.string().trim().max(200).nullable().transform(value => value || null),
  password: z.string().max(500).nullable().optional(),
  from_address: z.string().trim().toLowerCase().max(200).pipe(z.email()),
})

export const saveSmtp = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const input = parseBody(smtpSchema, body)
  const current = sendingOf(tenant).smtp
  const password = input.password === undefined ? (current?.password ?? null) : input.password || null
  const changed = !current || current.host !== input.host || current.port !== input.port || current.security !== input.security || current.username !== input.username || input.password !== undefined
  updateSending(tenant, sending => {
    sending.smtp = {
      host: input.host,
      port: input.port,
      security: input.security,
      username: input.username,
      password,
      has_password: !!password,
      from_address: input.from_address,
      // A different server or sign-in needs a new test
      status: changed ? 'untested' : (current?.status ?? 'untested'),
      checked_at: changed ? null : (current?.checked_at ?? null),
      problem: changed ? null : (current?.problem ?? null),
    }
  })
  audit(event, tenant, user, 'smtp_server', current ? `${current.host}:${current.port}` : null, `${input.host}:${input.port}`)
  return ok(view(tenant))
})

/** Connects and waits for the server's "220" greeting (the backend also signs in and sends a test email). */
function greet(host: string, port: number, tls: boolean): Promise<SmtpServer['problem']> {
  return new Promise(resolve => {
    let done = false
    const finish = (problem: SmtpServer['problem']) => {
      if (done) return
      done = true
      socket.destroy()
      resolve(problem)
    }
    const socket = tls ? connectTls({ host, port, servername: host, timeout: 6000 }) : connectTcp({ host, port, timeout: 6000 })
    socket.setEncoding('utf8')
    socket.once('data', (chunk: string) => finish(chunk.startsWith('220') ? null : 'not_smtp'))
    socket.once('timeout', () => finish('timeout'))
    socket.once('error', () => finish('unreachable'))
  })
}

export const testSmtp = defineMockRoute(async ({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const server = sendingOf(tenant).smtp
  if (!server) throw new MockError('FRM-GEN-1004')
  const problem = await greet(server.host, server.port, server.security === 'tls')
  const before = server.status
  updateSending(tenant, () => {
    server.status = problem ? 'failed' : 'working'
    server.problem = problem
    server.checked_at = new Date().toISOString()
  })
  if (before !== server.status) audit(event, tenant, user, 'smtp_status', before, server.status)
  return ok(view(tenant))
})

export const removeSmtp = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const server = sendingOf(tenant).smtp
  if (server) {
    updateSending(tenant, sending => (sending.smtp = null))
    audit(event, tenant, user, 'smtp_server', `${server.host}:${server.port}`, null)
  }
  return ok(view(tenant))
})

const modeSchema = z.object({ mode: z.enum(['formalie', 'domain', 'smtp']) })

export const setSendingMode = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const { mode } = parseBody(modeSchema, body)
  const sending = sendingOf(tenant)
  if ((mode === 'domain' && sending.domain?.status !== 'verified') || (mode === 'smtp' && sending.smtp?.status !== 'working')) throw new MockError('FRM-SET-1001', [{ field: 'mode', message: mode }])
  const before = sending.mode
  updateSending(tenant, item => (item.mode = mode))
  if (before !== mode) audit(event, tenant, user, 'sending_mode', before, mode)
  return ok(view(tenant))
})
