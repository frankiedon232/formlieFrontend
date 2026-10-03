/**
 * Mock onboarding (GET / PATCH /onboarding, POST /onboarding/finish). One state per workspace;
 * the seeded workspaces are already set up, new ones start at the first step. Every saved step is
 * recorded in the audit trail with before / after values.
 */
import { z } from 'zod'
import type { AuditChange } from '#shared/types/audit'
import {
  COMPANY_SIZES,
  DATE_FORMATS,
  INDUSTRIES,
  NUMBER_FORMATS,
  ONBOARDING_STEPS,
  type Onboarding,
  type OnboardingStep,
} from '#shared/types/onboarding'
import { isCountryCode, CURRENCY_CODES } from '#shared/utils/platform/countries'
import { STARTER_TEMPLATE_KEYS } from '#shared/utils/templates/starters'
import { APP_LOCALES } from '#shared/utils/i18n/locales'
import { requireAdmin } from '../core/auth'
import { actorOf, recordAudit } from '../core/audit'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { MOCK_USERS, SEEDED_TENANT_IDS, type MockTenant } from '../data/tenants'
import { completedUploadUrl } from './uploads'

const states = new Map<string, Onboarding>()

/** The organisation's website as set in onboarding / Settings → Company (public pages, F10). */
export const websiteOf = (tenant: MockTenant): string | null => stateOf(tenant).company.website ?? tenant.website ?? null

function stateOf(tenant: MockTenant): Onboarding {
  let state = states.get(tenant.id)
  if (!state) {
    // Seeded workspaces (they have history) count as set up; new signups start fresh.
    const seeded = SEEDED_TENANT_IDS.has(tenant.id)
    state = {
      status: seeded ? 'completed' : 'not_started',
      current_step: 'company',
      steps: Object.fromEntries(
        ONBOARDING_STEPS.map(step => [step, seeded ? 'done' : 'todo']),
      ) as Onboarding['steps'],
      company: { name: tenant.organisation.name, industry: null, size: null, country: null, website: tenant.website ?? null },
      branding: { logo_url: tenant.logo_url ?? null, brand_color: tenant.brand_color ?? null },
      localisation: {
        language: 'en',
        timezone: 'UTC',
        currency: 'USD',
        date_format: 'DD/MM/YYYY',
        number_format: '1,234.56',
        week_start: 'monday',
      },
      invites: [],
      first_form: { choice: null, template_key: null },
    }
    states.set(tenant.id, state)
  }
  return state
}

/** Field-level before / after for the audit trail. */
function diff<T extends object>(before: T, after: T, fields: (keyof T & string)[]): AuditChange[] {
  return fields
    .filter(field => before[field] !== after[field])
    .map(field => ({
      field,
      before: (before[field] ?? null) as AuditChange['before'],
      after: (after[field] ?? null) as AuditChange['after'],
    }))
}

const nextStep = (step: OnboardingStep): OnboardingStep =>
  ONBOARDING_STEPS[Math.min(ONBOARDING_STEPS.indexOf(step) + 1, ONBOARDING_STEPS.length - 1)]!

const company = z.object({
  name: z.string().trim().min(2).max(120),
  industry: z.enum(INDUSTRIES).nullable(),
  size: z.enum(COMPANY_SIZES).nullable(),
  country: z.string().refine(isCountryCode, 'Choose a country.').nullable(),
  website: z.url().max(200).nullable(),
})
const branding = z.object({
  logo_upload_id: z.string().nullable(),
  brand_color: z
    .string()
    .regex(/^#[0-9a-fA-F]{6}$/)
    .nullable(),
})
const localisation = z.object({
  language: z.enum(APP_LOCALES.map(item => item.code) as [string, ...string[]]),
  timezone: z.string().min(1).max(64),
  currency: z.string().refine(code => CURRENCY_CODES.includes(code), 'Choose a currency.'),
  date_format: z.enum(DATE_FORMATS),
  number_format: z.enum(NUMBER_FORMATS),
  week_start: z.enum(['monday', 'sunday', 'saturday']),
})
const team = z.object({
  invites: z
    .array(z.object({ email: z.email(), role: z.enum(['admin', 'member']) }))
    .max(20)
    .refine(list => new Set(list.map(i => i.email.toLowerCase())).size === list.length, 'Each email once.'),
})
const firstForm = z.object({
  choice: z.enum(['blank', 'template']).nullable(),
  template_key: z.enum(STARTER_TEMPLATE_KEYS as [string, ...string[]]).nullable(),
})

const patchSchema = z.object({
  step: z.enum(ONBOARDING_STEPS),
  action: z.enum(['save', 'skip']),
  data: z.unknown().optional(),
})

export const getOnboarding = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(stateOf(tenant))
})

export const patchOnboarding = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAdmin(event)
  const state = stateOf(tenant)
  const input = parseBody(patchSchema, body)
  const actor = actorOf(user)

  if (input.action === 'save') {
    if (input.step === 'company') {
      const data = parseBody(company, input.data)
      const changes = diff(state.company, data, ['name', 'industry', 'size', 'country', 'website'])
      state.company = data
      tenant.organisation.name = data.name
      if (changes.length)
        recordAudit(event, tenant, {
          action: 'workspace.updated',
          actor,
          resource: { type: 'workspace', id: tenant.id, name: data.name },
          changes,
          metadata: { source: 'onboarding' },
        })
    } else if (input.step === 'branding') {
      const data = parseBody(branding, input.data)
      const logoUrl = data.logo_upload_id ? completedUploadUrl(data.logo_upload_id, tenant.id) : null
      if (data.logo_upload_id && !logoUrl)
        throw new MockError('FRM-GEN-1002', [{ field: 'logo', message: 'Upload the logo again.' }])
      const next = { logo_url: logoUrl ?? state.branding.logo_url, brand_color: data.brand_color }
      const changes: AuditChange[] = [
        ...(logoUrl
          ? [{ field: 'logo', before: state.branding.logo_url ? 'set' : null, after: 'uploaded' }]
          : []),
        ...diff({ brand_colour: state.branding.brand_color }, { brand_colour: next.brand_color }, [
          'brand_colour',
        ]),
      ]
      state.branding = next
      tenant.logo_url = next.logo_url
      tenant.brand_color = next.brand_color
      if (changes.length)
        recordAudit(event, tenant, {
          action: 'settings.updated',
          actor,
          resource: { type: 'setting', id: null, name: 'Branding' },
          changes,
          metadata: { source: 'onboarding' },
        })
    } else if (input.step === 'localisation') {
      const data = parseBody(localisation, input.data)
      const changes = diff(state.localisation, data, [
        'language',
        'timezone',
        'currency',
        'date_format',
        'number_format',
        'week_start',
      ])
      state.localisation = data
      if (changes.length)
        recordAudit(event, tenant, {
          action: 'settings.updated',
          actor,
          resource: { type: 'setting', id: null, name: 'Localisation' },
          changes,
          metadata: { source: 'onboarding' },
        })
    } else if (input.step === 'team') {
      const { invites } = parseBody(team, input.data)
      const known = new Set(state.invites.map(i => i.email.toLowerCase()))
      const members = MOCK_USERS.filter(u => u.tenant_id === tenant.id).map(u => u.email.toLowerCase())
      const already = invites.find(i => members.includes(i.email.toLowerCase()))
      if (already)
        throw new MockError('FRM-GEN-1002', [
          { field: 'invites', message: `${already.email} is already in this workspace.` },
        ])
      for (const invite of invites.filter(i => !known.has(i.email.toLowerCase())))
        recordAudit(event, tenant, {
          action: 'users.invited',
          actor,
          resource: { type: 'user', id: null, name: invite.email },
          metadata: { role: invite.role, source: 'onboarding' },
        })
      state.invites = invites
    } else {
      const data = parseBody(firstForm, input.data)
      state.first_form = data as Onboarding['first_form']
    }
    state.steps[input.step] = 'done'
  } else {
    if (state.steps[input.step] !== 'done') state.steps[input.step] = 'skipped'
  }

  state.current_step = nextStep(input.step)
  if (state.status === 'not_started') state.status = 'in_progress'
  return ok(state)
})

export const finishOnboarding = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAdmin(event)
  const state = stateOf(tenant)
  if (state.status !== 'completed') {
    state.status = 'completed'
    recordAudit(event, tenant, {
      action: 'workspace.setup_completed',
      actor: actorOf(user),
      resource: { type: 'workspace', id: tenant.id, name: tenant.name },
      metadata: {
        done: String(Object.values(state.steps).filter(s => s === 'done').length),
        skipped: String(Object.values(state.steps).filter(s => s === 'skipped').length),
      },
    })
  }
  return ok(state)
})
