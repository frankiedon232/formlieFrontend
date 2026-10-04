/**
 * Invite-only forms and member passes (F10 M3, decision 96):
 *   GET    /forms/:id/invites                     the invitations and their status
 *   POST   /forms/:id/invites                     invite people { people: [{ email, name? }] } → personal links (emailed; dev: returned)
 *   POST   /forms/:id/invites/:inviteId/resend    a new personal link (the old one stops working)
 *   DELETE /forms/:id/invites/:inviteId           revoke (the link stops working)
 *   POST   /forms/pass                            { key } → a 2-minute sign-in pass for an organisation-only form
 * Tokens are stored as hashes; the personal link exists only in the invitation. Audited as forms.shared.
 */
import { z } from 'zod'
import type { FormInvitation } from '#shared/types/forms'
import { formLink, publicHosts } from '#shared/utils/urls/public'
import { requireAuth } from '../core/auth'
import { actorOf, recordAudit } from '../core/audit'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { hashToken, issuePass, newInviteToken, type FormInvite } from '../data/formAccess'
import { requireLevel } from '../data/formPermissions'
import { formsOf, saveForms, type StoredForm } from '../data/formStore'
import type { MockTenant, MockUser } from '../data/tenants'

const MAX_INVITES = 500

/** A form of this workspace, with at least this people-access level (decision 97). */
function findForm(tenant: MockTenant, user: MockUser, id: string | undefined, need: 'view' | 'edit' = 'edit'): StoredForm {
  const form = formsOf(tenant).forms.find(item => item.id === id && !item.deleted_at)
  if (!form) throw new MockError('FRM-GEN-1004')
  requireLevel(form, user, need)
  return form
}

const statusOf = (invite: FormInvite): FormInvitation['status'] =>
  invite.revoked_at ? 'revoked' : invite.responded_at ? 'responded' : invite.opened_at ? 'opened' : 'invited'
const viewOf = (invite: FormInvite): FormInvitation => ({
  id: invite.id,
  email: invite.email,
  name: invite.name,
  status: statusOf(invite),
  sent_at: invite.sent_at,
  opened_at: invite.opened_at,
  responded_at: invite.responded_at,
})
const listOf = (form: StoredForm) => [...(form.invites ?? [])].sort((a, b) => b.sent_at.localeCompare(a.sent_at)).map(viewOf)

/** The personal link: the form's current address + the invitation token. */
function personalLink(event: Parameters<typeof requireAuth>[0], tenant: MockTenant, form: StoredForm, token: string) {
  const port = getRequestHost(event, { xForwardedHost: true }).split(':')[1] ?? ''
  return `${formLink(publicHosts(useRuntimeConfig(event).public, port), form.custom_link || form.public_key, 'fill', tenant.subdomain ?? null)}?invite=${token}`
}

/**
 * Invitations are their own list: changing them doesn't bump the form's row_version, so share
 * settings being edited on the same page still save (no false "changed by someone else").
 */
function audit(event: Parameters<typeof requireAuth>[0], tenant: MockTenant, user: MockUser, form: StoredForm, field: string, after: string) {
  form.updated_at = new Date().toISOString()
  saveForms()
  recordAudit(event, tenant, { action: 'forms.shared', actor: actorOf(user), resource: { type: 'form', id: form.id, name: form.name }, changes: [{ field, before: null, after }] })
}

/** GET /forms/:id/invites */
export const listInvites = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  return ok(listOf(findForm(tenant, user, getRouterParam(event, 'id'), 'view')))
})

const inviteBody = z.object({
  people: z
    .array(z.object({ email: z.email().max(200), name: z.string().trim().max(120).optional() }))
    .min(1)
    .max(200),
})

/** POST /forms/:id/invites — people already invited (and not revoked) are skipped, not invited twice. */
export const createInvites = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const form = findForm(tenant, user, getRouterParam(event, 'id'))
  const input = parseBody(inviteBody, body)
  form.invites ??= []
  const active = new Set(form.invites.filter(item => !item.revoked_at).map(item => item.email))
  if (active.size + input.people.length > MAX_INVITES) throw new MockError('FRM-GEN-1002', [{ field: 'people', message: `At most ${MAX_INVITES} invitations per form.` }])
  const links: { email: string; url: string }[] = []
  const skipped: string[] = []
  for (const person of input.people) {
    const email = person.email.trim().toLowerCase()
    if (active.has(email)) {
      skipped.push(email)
      continue
    }
    active.add(email)
    const token = newInviteToken()
    const now = new Date().toISOString()
    form.invites.push({ id: crypto.randomUUID(), email, name: person.name || null, token_hash: hashToken(token), created_at: now, sent_at: now, opened_at: null, responded_at: null, revoked_at: null })
    links.push({ email, url: personalLink(event, tenant, form, token) })
  }
  if (links.length) audit(event, tenant, user, form, 'invitations', `${links.length} invited`)
  // A real backend emails each link; development shows them so they can be copied.
  return ok({ invitations: listOf(form), created: links.length, skipped }, import.meta.dev ? { dev_links: links } : {}, 201)
})

function inviteOf(form: StoredForm, id: string | undefined): FormInvite {
  const invite = (form.invites ?? []).find(item => item.id === id)
  if (!invite) throw new MockError('FRM-GEN-1004')
  return invite
}

/** POST /forms/:id/invites/:inviteId/resend — a new personal link; the previous one stops working. */
export const resendInvite = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const form = findForm(tenant, user, getRouterParam(event, 'id'))
  const invite = inviteOf(form, getRouterParam(event, 'inviteId'))
  if (invite.revoked_at) throw new MockError('FRM-FORM-1007')
  const token = newInviteToken()
  invite.token_hash = hashToken(token)
  invite.sent_at = new Date().toISOString()
  audit(event, tenant, user, form, 'invitation_resent', invite.email)
  return ok({ invitations: listOf(form) }, import.meta.dev ? { dev_links: [{ email: invite.email, url: personalLink(event, tenant, form, token) }] } : {})
})

/**
 * DELETE /forms/:id/invites/:inviteId — the invitation link stops working (a response already sent stays).
 * `?remove=1` on a revoked invitation takes it off the list (owner, 2026-10-04); an active one must be revoked first.
 */
export const revokeInvite = defineMockRoute(({ event, query }) => {
  const { user, tenant } = requireAuth(event)
  const form = findForm(tenant, user, getRouterParam(event, 'id'))
  const invite = inviteOf(form, getRouterParam(event, 'inviteId'))
  if (query.remove === '1') {
    if (!invite.revoked_at) throw new MockError('FRM-FORM-1007')
    form.invites = (form.invites ?? []).filter(item => item.id !== invite.id)
    audit(event, tenant, user, form, 'invitation_removed', invite.email)
    return ok({ invitations: listOf(form) })
  }
  if (!invite.revoked_at) {
    invite.revoked_at = new Date().toISOString()
    audit(event, tenant, user, form, 'invitation_revoked', invite.email)
  }
  return ok({ invitations: listOf(form) })
})

const passBody = z.object({ key: z.string().min(3).max(80) })

/** POST /forms/pass — a signed-in member asks to open an organisation-only form of their workspace. */
export const formPass = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const { key } = parseBody(passBody, body)
  const form = formsOf(tenant).forms.find(item => (item.public_key === key || item.custom_link === key) && !item.deleted_at)
  // Another workspace's form: the member's sign-in doesn't open it.
  if (!form) throw new MockError('FRM-PERM-1001')
  const port = getRequestHost(event, { xForwardedHost: true }).split(':')[1] ?? ''
  const fill = formLink(publicHosts(useRuntimeConfig(event).public, port), form.custom_link || form.public_key, 'fill', tenant.subdomain ?? null)
  return ok({ url: `${fill}?pass=${encodeURIComponent(issuePass(form, user))}` })
})
