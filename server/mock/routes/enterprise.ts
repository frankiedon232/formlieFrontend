/**
 * Enterprise enquiries (F24, owner 2026-10-10): "Contact us" on the Enterprise plan opens a form inside the app;
 * what is sent goes to the Formalie team, who read and answer it in the platform admin (F23). Kept in
 * `.data/mock/enquiries.json` (platform-wide, with the workspace it came from). Admins only.
 *
 *   GET  /billing/enterprise-enquiries     this workspace's enquiries (newest first): what was sent and its state
 *   POST /billing/enterprise-enquiries     EnterpriseEnquiry → { id, status: new, received_at }
 */
import { z } from 'zod'
import type { EnterpriseEnquiry } from '#shared/types/billing'
import { actorOf, recordAudit } from '../core/audit'
import { requireAuth } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { loadPersisted, savePersisted } from '../core/persist'
import { parseBody } from '../core/validate'

interface StoredEnquiry extends EnterpriseEnquiry {
  id: string
  tenant_id: string
  workspace: string
  by: string
  status: 'new' | 'contacted' | 'closed'
  received_at: string
}
const enquiries: StoredEnquiry[] = loadPersisted<StoredEnquiry[]>('enquiries', [])
const save = () => savePersisted('enquiries', () => enquiries)

const text = (max: number) =>
  z
    .string()
    .trim()
    .max(max)
    .nullable()
    .optional()
    .transform(value => value || null)
const schema = z.object({
  company: z.string().trim().min(2).max(160),
  name: z.string().trim().min(2).max(120),
  email: z.string().trim().toLowerCase().pipe(z.email()),
  phone: text(40),
  role: text(120),
  country: text(80),
  size: z.enum(['1-50', '51-200', '201-1000', '1001-5000', '5000+']),
  responses_per_month: z.enum(['under_100k', '100k_1m', '1m_10m', 'over_10m']),
  needs: z.array(z.enum(['sso', 'dedicated', 'residency', 'sla', 'security', 'invoice', 'onboarding', 'custom_limits'])).max(8),
  data_residency: text(120),
  message: z.string().trim().min(10).max(4000),
  start: z.enum(['now', 'quarter', 'later']),
})

export const listEnquiries = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  return ok(enquiries.filter(item => item.tenant_id === tenant.id).map(({ tenant_id: _t, ...item }) => item))
})

export const sendEnquiry = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const input = parseBody(schema, body)
  // The same enquiry again within a minute is a double send
  const recent = enquiries.find(item => item.tenant_id === tenant.id && item.status === 'new' && Date.now() - Date.parse(item.received_at) < 60_000)
  if (recent) throw new MockError('FRM-BILL-1003')
  const enquiry: StoredEnquiry = { ...input, id: crypto.randomUUID(), tenant_id: tenant.id, workspace: tenant.subdomain, by: user.email, status: 'new', received_at: new Date().toISOString() }
  enquiries.unshift(enquiry)
  save()
  recordAudit(event, tenant, { action: 'settings.updated', actor: actorOf(user), resource: { type: 'setting', id: enquiry.id, name: 'Enterprise enquiry' }, changes: [{ field: 'enterprise_enquiry', before: null, after: input.company }] })
  return ok({ id: enquiry.id, status: enquiry.status, received_at: enquiry.received_at })
})
