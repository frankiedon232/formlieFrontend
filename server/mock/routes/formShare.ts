/**
 * Share settings (F10 M3, docs/API-CONTRACT.md → Sharing):
 *   GET  /forms/:id/share               access, password set?, response limit, custom link, availability
 *   PUT  /forms/:id/share               change them (row_version), audited as forms.shared, never the password
 *   GET  /forms/:id/share/link-check    is a custom link free? (+ up to three free suggestions)
 * Passwords are stored as scrypt hashes; changing one signs everyone out of the form (version).
 */
import { randomBytes, scryptSync } from 'node:crypto'
import { z } from 'zod'
import type { AuditChange } from '#shared/types/audit'
import { channelsOf, FORM_CHANNELS, type CustomLinkCheck, type FormShareSettings } from '#shared/types/forms'
import { customLinkProblem, FORM_KEY_PATTERN, newShortCode, tidyCustomLink } from '#shared/utils/urls/public'
import { MAX_EMBED_DOMAINS, normaliseEmbedDomain } from '#shared/utils/urls/embed-domains'
import { requireAuth } from '../core/auth'
import { SEO_DESCRIPTION_MAX, SEO_TITLE_MAX, seoDefaults } from '../data/formSeo'
import { completedUploadUrl } from './uploads'
import { actorOf, recordAudit } from '../core/audit'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { formsOf, saveForms, type StoredForm } from '../data/formStore'
import { isRetiredShortCode, retireShortCode } from '../data/shortCodeStore'
import { MOCK_TENANTS, MOCK_USERS, type MockTenant, type MockUser } from '../data/tenants'
import { isWorkspaceAdmin, requireLevel } from '../data/formPermissions'
import { MOCK_OWNERS } from '../data/forms'

/** A form of this workspace that this person can edit: sharing is editors only (decision 97). */
function findForm(tenant: MockTenant, user: MockUser, id: string | undefined): StoredForm {
  const form = formsOf(tenant).forms.find(item => item.id === id && !item.deleted_at)
  if (!form) throw new MockError('FRM-GEN-1004')
  requireLevel(form, user, 'edit')
  return form
}

export const hashPassword = (password: string, salt: string) => scryptSync(password, salt, 32).toString('base64')

const settingsOf = (form: StoredForm, tenant: MockTenant): FormShareSettings => ({
  channels: channelsOf(form),
  access: form.access ?? 'public',
  has_password: !!form.password,
  password_changed_at: form.password?.changed_at ?? null,
  response_limit: form.response_limit ?? null,
  responses_count: form.responses_count,
  custom_link: form.custom_link ?? null,
  opens_at: form.opens_at,
  closes_at: form.closes_at,
  row_version: form.row_version,
  embed_domains: form.embed_domains ?? [],
  people: peopleOf(form, tenant),
  seo: {
    title: form.seo?.title ?? null,
    description: form.seo?.description ?? null,
    image_upload_id: form.seo?.image_upload_id ?? null,
    image_url: form.seo?.image_upload_id ? completedUploadUrl(form.seo.image_upload_id, tenant.id) : null,
    noindex: !!form.seo?.noindex,
    default_title: seoDefaults(form).title,
    default_description: seoDefaults(form).description,
  },
  short_link: form.short_code ? { code: form.short_code, clicks: form.short_clicks ?? 0, created_at: form.short_created_at ?? form.updated_at } : null,
})

// ── People access (decision 97) ─────────────────────────────────────────────────────────
type Person = { id: string; name: string; email: string }
/** Everyone who can be given access: the workspace's people (plus the sample form owners of the mock). */
function peopleIn(tenant: MockTenant): Person[] {
  const domain = `${tenant.subdomain}.test`
  return [
    ...MOCK_USERS.filter(user => user.tenant_id === tenant.id && !user.disabled).map(user => ({ id: user.id, name: `${user.first_name} ${user.last_name}`.trim(), email: user.email })),
    ...MOCK_OWNERS.map(owner => ({ id: owner.id, name: owner.name, email: `${owner.name.toLowerCase().replace(/\s+/g, '.')}@${domain}` })),
  ]
}
function peopleOf(form: StoredForm, tenant: MockTenant): FormShareSettings['people'] {
  const people = peopleIn(tenant)
  const admins = MOCK_USERS.filter(user => user.tenant_id === tenant.id && !user.disabled && isWorkspaceAdmin(user))
  const always: FormShareSettings['people']['always'] = admins.map(user => ({ user: people.find(person => person.id === user.id)!, reason: 'workspace_admin' as const }))
  if (!admins.some(user => user.id === form.owner.id)) {
    const owner = people.find(person => person.id === form.owner.id) ?? { id: form.owner.id, name: form.owner.name, email: '' }
    always.push({ user: owner, reason: 'form_owner' })
  }
  const grants = (form.grants ?? []).flatMap(grant => {
    const user = people.find(person => person.id === grant.user_id)
    return user ? [{ user, level: grant.level }] : []
  })
  return { team_access: form.team_access ?? 'edit', grants, always }
}

/**
 * Workspaces whose forms live on the same address (owner, 2026-10-04): a workspace with its own
 * subdomain has its links to itself (remedylegal.… and datalinks.… can both have /feedback);
 * workspaces without one share forms.formalie.com, so their links must differ from each other.
 */
const sameHost = (tenant: MockTenant) => (tenant.subdomain ? [tenant] : MOCK_TENANTS.filter(item => !item.subdomain))

/** The form already answering to this address on the same host (custom link, or a key that reads the same). */
function holderOf(value: string, exceptId: string, tenant: MockTenant): { tenant: MockTenant; form: StoredForm } | null {
  for (const owner of sameHost(tenant)) {
    const form = formsOf(owner).forms.find(item => item.id !== exceptId && !item.deleted_at && (item.custom_link === value || item.public_key === value))
    if (form) return { tenant: owner, form }
  }
  return null
}
const linkTaken = (value: string, exceptId: string, tenant: MockTenant) => !!holderOf(value, exceptId, tenant)

/** Up to three free links close to what was typed: with the organisation's name, the year, a number. */
function suggestionsFor(value: string, formId: string, tenant: MockTenant): string[] {
  const base = tidyCustomLink(value)
  if (base.length < 2) return []
  const org = tidyCustomLink(tenant.subdomain || tenant.name).slice(0, 20)
  const year = new Date().getFullYear()
  const candidates = [org && `${org}-${base}`, org && `${base}-${org}`, `${base}-${year}`, `${base}-form`]
  for (let n = 2; n < 50; n++) candidates.push(`${base}-${n}`)
  const free: string[] = []
  for (const candidate of candidates) {
    if (!candidate) continue
    const link = tidyCustomLink(candidate)
    if (!free.includes(link) && !customLinkProblem(link) && !linkTaken(link, formId, tenant)) free.push(link)
    if (free.length === 3) break
  }
  return free
}

function check(value: string, formId: string, tenant: MockTenant): CustomLinkCheck {
  const problem = customLinkProblem(value)
  // Reserved words still get suggestions; unreadable input doesn't.
  if (problem === 'invalid') return { value, available: false, reason: 'invalid', suggestions: [], taken_by: null }
  const holder = problem ? null : holderOf(value, formId, tenant)
  if (!problem && !holder) return { value, available: true, reason: null, suggestions: [], taken_by: null }
  return {
    value,
    available: false,
    reason: problem ?? 'taken',
    suggestions: suggestionsFor(value, formId, tenant),
    // Which of your forms uses it, never another organisation's form.
    taken_by: holder && holder.tenant.id === tenant.id ? { id: holder.form.id, name: holder.form.name, status: holder.form.status, link: holder.form.custom_link === value } : null,
  }
}

/** GET /forms/:id/share */
export const getShare = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  return ok(settingsOf(findForm(tenant, user, getRouterParam(event, 'id')), tenant))
})

/** GET /forms/:id/share/link-check?value= */
export const checkLink = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const form = findForm(tenant, user, getRouterParam(event, 'id'))
  // Query values arrive inside the encrypted envelope (ctx.query), not in the address.
  const value = String(query.value ?? '').slice(0, 80)
  return ok(check(value, form.id, tenant))
})

const shareSchema = z.object({
  row_version: z.number().int().optional(),
  access: z.enum(['public', 'password', 'invite', 'organisation']).optional(),
  /** A new password (8–100 characters); never returned. */
  password: z.string().min(8).max(100).optional(),
  response_limit: z.number().int().min(2).max(1_000_000).nullable().optional(),
  custom_link: z.string().max(80).nullable().optional(),
  /** Search & link preview; empty text = from the form. */
  seo: z
    .object({
      title: z.string().max(SEO_TITLE_MAX).nullable(),
      description: z.string().max(SEO_DESCRIPTION_MAX).nullable(),
      image_upload_id: z.string().max(64).nullable(),
      noindex: z.boolean(),
    })
    .optional(),
  /** People access: the workspace default and people given access. */
  people: z
    .object({
      team_access: z.enum(['edit', 'view', 'none']),
      grants: z.array(z.object({ user_id: z.string().max(64), level: z.enum(['edit', 'view', 'responses']) })).max(500),
    })
    .optional(),
  /** Where people can answer (at least one). */
  channels: z.array(z.enum(FORM_CHANNELS)).min(1).max(3).optional(),
  /** Websites allowed to show the embed; [] = any website. */
  embed_domains: z.array(z.string().max(253)).max(MAX_EMBED_DOMAINS).optional(),
})

/** PUT /forms/:id/share */
export const saveShare = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const form = findForm(tenant, user, getRouterParam(event, 'id'))
  const input = parseBody(shareSchema, body)
  if (input.row_version !== undefined && input.row_version !== form.row_version) throw new MockError('FRM-GEN-1009')
  const changes: AuditChange[] = []

  if (input.password !== undefined) {
    const salt = randomBytes(16).toString('base64')
    form.password = { hash: hashPassword(input.password, salt), salt, version: (form.password?.version ?? 0) + 1, changed_at: new Date().toISOString() }
    // Never the password itself, only that it changed.
    changes.push({ field: 'password', before: null, after: 'changed' })
  }
  if (input.access !== undefined && input.access !== (form.access ?? 'public')) {
    if (input.access === 'password' && !form.password)
      throw new MockError('FRM-GEN-1002', [{ field: 'password', message: 'Set a password for this form.' }])
    changes.push({ field: 'access', before: form.access ?? 'public', after: input.access })
    form.access = input.access
  }
  if (input.response_limit !== undefined && input.response_limit !== (form.response_limit ?? null)) {
    changes.push({ field: 'response_limit', before: form.response_limit == null ? null : String(form.response_limit), after: input.response_limit == null ? null : String(input.response_limit) })
    form.response_limit = input.response_limit
  }
  if (input.custom_link !== undefined) {
    const value = input.custom_link?.trim() || null
    if (value !== (form.custom_link ?? null)) {
      if (value) {
        const result = check(value, form.id, tenant)
        if (!result.available)
          throw new MockError(result.reason === 'taken' ? 'FRM-FORM-1006' : 'FRM-GEN-1002', [{ field: 'custom_link', message: result.reason ?? 'invalid' }])
        // A link that reads like a key would be ambiguous.
        if (FORM_KEY_PATTERN.test(value) && /[A-Z]/.test(value)) throw new MockError('FRM-GEN-1002', [{ field: 'custom_link', message: 'invalid' }])
      }
      changes.push({ field: 'custom_link', before: form.custom_link ?? null, after: value })
      form.custom_link = value
    }
  }

  if (input.people !== undefined) {
    const known = new Set(peopleIn(tenant).map(person => person.id))
    if (input.people.grants.some(grant => !known.has(grant.user_id))) throw new MockError('FRM-GEN-1002', [{ field: 'people', message: 'Unknown person.' }])
    const before = form.team_access ?? 'edit'
    if (before !== input.people.team_access) changes.push({ field: 'team_access', before, after: input.people.team_access })
    const describe = (grants: { user_id: string; level: string }[]) => grants.map(grant => `${grant.user_id}:${grant.level}`).sort().join(',')
    const grants = [...new Map(input.people.grants.map(grant => [grant.user_id, grant])).values()]
    if (describe(form.grants ?? []) !== describe(grants)) {
      const names = (list: { user_id: string; level: string }[]) => list.map(grant => `${peopleIn(tenant).find(person => person.id === grant.user_id)?.name ?? '?'} (${grant.level})`).join(', ') || null
      changes.push({ field: 'people_access', before: names(form.grants ?? []), after: names(grants) })
      form.grants = grants.map(grant => ({ ...grant, granted_at: (form.grants ?? []).find(item => item.user_id === grant.user_id)?.granted_at ?? new Date().toISOString() }))
    }
    form.team_access = input.people.team_access
  }
  if (input.seo !== undefined) {
    const next = {
      title: input.seo.title?.trim() || null,
      description: input.seo.description?.trim() || null,
      image_upload_id: input.seo.image_upload_id,
      noindex: input.seo.noindex,
    }
    // The image must be a finished upload of this workspace.
    if (next.image_upload_id && !completedUploadUrl(next.image_upload_id, tenant.id)) throw new MockError('FRM-GEN-1002', [{ field: 'seo.image_upload_id', message: 'Upload the image again.' }])
    const before = form.seo ?? { title: null, description: null, image_upload_id: null, noindex: false }
    for (const field of ['title', 'description', 'noindex'] as const)
      if (before[field] !== next[field]) changes.push({ field: `seo_${field}`, before: before[field] == null ? null : String(before[field]), after: next[field] == null ? null : String(next[field]) })
    if (before.image_upload_id !== next.image_upload_id) changes.push({ field: 'seo_image', before: before.image_upload_id ? 'image' : null, after: next.image_upload_id ? 'image' : null })
    form.seo = next
  }
  if (input.channels !== undefined) {
    const next = FORM_CHANNELS.filter(channel => input.channels!.includes(channel))
    const before = channelsOf(form)
    if (next.join() !== before.join()) {
      changes.push({ field: 'channels', before: before.join(', '), after: next.join(', ') })
      form.channels = next
    }
  }
  if (input.embed_domains !== undefined) {
    const domains = [...new Set(input.embed_domains.map(normaliseEmbedDomain))]
    if (domains.some(domain => !domain)) throw new MockError('FRM-GEN-1002', [{ field: 'embed_domains', message: 'invalid' }])
    const before = (form.embed_domains ?? []).join(', ')
    if (domains.join(', ') !== before) {
      changes.push({ field: 'embed_domains', before: before || null, after: domains.join(', ') || null })
      form.embed_domains = domains as string[]
    }
  }
  if (changes.length) {
    form.row_version++
    form.updated_at = new Date().toISOString()
    saveForms()
    recordAudit(event, tenant, { action: 'forms.shared', actor: actorOf(user), resource: { type: 'form', id: form.id, name: form.name }, changes })
  }
  return ok(settingsOf(form, tenant))
})

// ── Short link (F10 M3) ─────────────────────────────────────────────────────────────────
/** In use by any form of any organisation (deleted forms included), or retired. */
const codeTaken = (code: string) => isRetiredShortCode(code) || MOCK_TENANTS.some(tenant => formsOf(tenant).forms.some(form => form.short_code === code))

function shortLinkChange(event: Parameters<typeof requireAuth>[0], create: boolean) {
  const { user, tenant } = requireAuth(event)
  const form = findForm(tenant, user, getRouterParam(event, 'id'))
  const before = form.short_code ?? null
  if (create && !form.short_code) {
    let code = newShortCode()
    while (codeTaken(code)) code = newShortCode()
    form.short_code = code
    form.short_clicks = 0
    form.short_created_at = new Date().toISOString()
  } else if (!create && form.short_code) {
    // The old code stops working and is never handed out again (data/shortCodeStore.ts).
    retireShortCode(form.short_code)
    form.short_code = null
    form.short_clicks = 0
    form.short_created_at = null
  }
  if ((form.short_code ?? null) !== before) {
    form.row_version++
    form.updated_at = new Date().toISOString()
    saveForms()
    recordAudit(event, tenant, { action: 'forms.shared', actor: actorOf(user), resource: { type: 'form', id: form.id, name: form.name }, changes: [{ field: 'short_link', before, after: form.short_code ?? null }] })
  }
  return ok(settingsOf(form, tenant), {}, create && !before ? 201 : 200)
}

/** POST /forms/:id/short-link, create the form's short link (or return the one it has). */
export const createShortLink = defineMockRoute(({ event }) => shortLinkChange(event, true))
/** DELETE /forms/:id/short-link, remove it; the code stops working. */
export const removeShortLink = defineMockRoute(({ event }) => shortLinkChange(event, false))
