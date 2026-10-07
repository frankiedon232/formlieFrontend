/**
 * Mock forms + folders (docs/API-CONTRACT.md → Forms). Every change bumps `row_version`
 * (mismatch → FRM-GEN-1009) and is recorded in the audit trail with before / after values.
 */
import { inScope, organisationForNewForm } from '../data/organisationStore'
import type { H3Event } from 'h3'
import { newPublicKey } from '#shared/utils/urls/public'
import { z } from 'zod'
import type { AuditChange } from '#shared/types/audit'
import type {
  FormBulkResult,
  FormFacets,
  FormFolder,
  FormLifecycleAction,
  FormStatus,
} from '#shared/types/forms'
import { formSchemaV1 } from '#shared/utils/forms/schema'
import { FOLDER_COLOR_KEYS, type FolderColor } from '#shared/utils/forms/folders'
import { allTemplates, blankFormSchema, schemaForTemplate } from '../data/templateStore'

import type { AuditAction } from '#shared/utils/audit/events'
import { requireAuth } from '../core/auth'
import { actorOf, recordAudit } from '../core/audit'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { formsOf, saveForms, summaryOf, uniqueSlug, type StoredForm } from '../data/formStore'
import { settingsOf } from '../data/settingsStore'
import { themeForNewForm } from './themes'
import { retireShortCode } from '../data/shortCodeStore'
import type { MockTenant, MockUser } from '../data/tenants'
import { canSee, levelOf, requireLevel } from '../data/formPermissions'
import { FORMALIE_MARK, storageMarks } from '../data/destinationStore'

type Query = Record<string, unknown>
const list = (query: Query, key: string) => {
  const value = query[`filter[${key}]`]
  return typeof value === 'string' && value ? value.split(',') : null
}
const day = (value: unknown, end: boolean) =>
  typeof value === 'string' && value ? Date.parse(`${value}T${end ? '23:59:59' : '00:00:00'}Z`) : null

/** A form of this workspace the person may work on (people access, decision 97: changes need "edit"). */
function findForm(tenant: MockTenant, user: MockUser, id: string | undefined, { trash = false, need = 'edit' as 'edit' | 'view' | 'responses' } = {}): StoredForm {
  const form = formsOf(tenant).forms.find(item => item.id === id)
  if (!form || !!form.deleted_at !== trash) throw new MockError('FRM-GEN-1004')
  requireLevel(form, user, need)
  return form
}
/** The summary with what this person may do (my_access). */
const summaryFor = (form: StoredForm, user: MockUser) => ({ ...summaryOf(form), my_access: levelOf(form, user) })

function checkVersion(form: StoredForm, version: number | undefined) {
  if (version !== undefined && version !== form.row_version) throw new MockError('FRM-GEN-1009')
}

function touch(form: StoredForm) {
  form.row_version++
  form.updated_at = new Date().toISOString()
  saveForms()
}

function audit(
  event: H3Event,
  tenant: MockTenant,
  user: MockUser,
  action: AuditAction,
  form: StoredForm,
  changes: AuditChange[] = [],
  metadata: Record<string, string> = {},
) {
  recordAudit(event, tenant, {
    action,
    actor: actorOf(user),
    resource: { type: 'form', id: form.id, name: form.name },
    changes,
    metadata,
  })
}

const ownerOf = (user: MockUser) => ({ id: user.id, name: `${user.first_name} ${user.last_name}`.trim() })

// ── Lists ─────────────────────────────────────────────────────────────────────────

/** GET /forms, filters: status, folder_id (`none` = no folder), owner_id, tag (comma = any of), trash=1; from/to on updated_at. */
export const listForms = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const status = list(query, 'status')
  const folder = list(query, 'folder_id')
  const owner = list(query, 'owner_id')
  const tag = list(query, 'tag')
  const template = list(query, 'template')
  const trash = query['filter[trash]'] === '1'
  const from = day(query.from, false)
  const to = day(query.to, true)

  const filtered = formsOf(tenant).forms.filter(form => {
    const updated = Date.parse(form.updated_at)
    return (
      canSee(form, user) &&
      inScope(tenant, form) &&
      !!form.deleted_at === trash &&
      // Archived forms only show when asked for explicitly (and always in Trash).
      (trash || (status ? status.includes(form.status) : form.status !== 'archived')) &&
      (!folder || folder.includes(form.folder?.id ?? 'none')) &&
      (!owner || owner.includes(form.owner.id)) &&
      (!tag || form.tags.some(t => tag.includes(t))) &&
      (!template || template.includes(form.template_key ?? '')) &&
      (from === null || updated >= from) &&
      (to === null || updated <= to)
    )
  })

  const { data, meta } = paginate<StoredForm>(
    filtered,
    { sort: trash ? '-deleted_at' : '-updated_at', ...query },
    (form, q) => form.name.toLowerCase().includes(q) || form.slug.includes(q) || form.tags.includes(q),
  )
  const marks = storageMarks(tenant)
  return ok(data.map(form => ({ ...summaryFor(form, user), storage: marks.get(form.id) ?? FORMALIE_MARK })), meta)
})

export const formFacets = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const forms = formsOf(tenant).forms.filter(form => !form.deleted_at && inScope(tenant, form) && canSee(form, user))
  const owners = new Map(forms.map(form => [form.owner.id, form.owner]))
  return ok<FormFacets>({
    owners: [...owners.values()].sort((a, b) => a.name.localeCompare(b.name)),
    tags: [...new Set(forms.flatMap(form => form.tags))].sort(),
    templates: allTemplates(tenant, 'en')
      .filter(item => forms.some(form => form.template_key === item.key))
      .map(item => ({ key: item.key, name: item.name }))
      .sort((a, b) => a.name.localeCompare(b.name)),
  })
})

export const getForm = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const form = formsOf(tenant).forms.find(item => item.id === getRouterParam(event, 'id'))
  if (!form) throw new MockError('FRM-GEN-1004')
  const level = requireLevel(form, user, 'responses')
  // Responses only: no questions or design.
  return ok({ ...summaryFor(form, user), template_key: form.template_key, schema: level === 'responses' ? null : form.schema })
})

// ── Create ────────────────────────────────────────────────────────────────────────

const name = z.string().trim().min(1, 'Give the form a name.').max(120)
const createSchema = z.object({
  name,
  folder_id: z.string().nullable().optional(),
  /** A system template key or a workspace template (`ws_…`); checked against the catalogue. */
  template_key: z.string().max(80).nullable().optional(),
  label_position: z.enum(['top', 'left']).optional(),
  /** The creator's language: a system template starts in it (F9). */
  language: z.string().regex(/^[a-z]{2}(-[A-Z]{2})?$/).optional(),
})
const importSchema = z.object({ name, folder_id: z.string().nullable().optional(), schema: formSchemaV1 })

function folderRef(tenant: MockTenant, id: string | null | undefined): FormFolder | null {
  if (!id) return null
  const folder = formsOf(tenant).folders.find(item => item.id === id)
  if (!folder) throw new MockError('FRM-GEN-1002', [{ field: 'folder_id', message: 'Choose a folder.' }])
  return { id: folder.id, name: folder.name }
}

function newForm(
  tenant: MockTenant,
  user: MockUser,
  input: {
    name: string
    folder: FormFolder | null
    template_key?: string | null
    schema?: StoredForm['schema']
    /** Language of the person creating it: templates start in that language. */
    language?: string
  },
): StoredForm {
  const store = formsOf(tenant)
  const now = new Date().toISOString()
  const form: StoredForm = {
    id: crypto.randomUUID(),
    name: input.name,
    slug: uniqueSlug(store, input.name),
    public_key: newPublicKey(),
    opens_at: null,
    closes_at: null,
    custom_link: null,
    access: 'public',
    response_limit: null,
    short_code: null,
    status: 'draft',
    has_unpublished_changes: false,
    folder: input.folder,
    owner: ownerOf(user),
    tags: [],
    responses_count: 0,
    completion_rate: 0,
    created_at: now,
    updated_at: now,
    row_version: 1,
    deleted_at: null,
    previous_status: null,
    schema: input.schema ?? (input.template_key ? schemaForTemplate(tenant, input.template_key, input.language) : null) ?? blankFormSchema(input.language),
    template_key: input.template_key ?? null,
    organisation_id: organisationForNewForm(tenant),
  }
  store.forms.unshift(form)
  saveForms()
  return form
}

/**
 * Settings → Form defaults (F14 M5): a new blank or template form starts with the workspace's settings,
 * theme, thank-you text, response emails and allowed websites. What the dialog chose (label position)
 * and a template's own design win. Imports and copies keep their own.
 */
function withFormDefaults(tenant: MockTenant, form: StoredForm, labelPosition?: 'top' | 'left') {
  const defaults = settingsOf(tenant).form_defaults
  if (form.schema) {
    const settings = form.schema.settings ?? {}
    form.schema.settings = {
      ...settings,
      progress_bar: defaults.settings.progress_bar,
      save_resume: defaults.settings.save_resume,
      field_icons: defaults.settings.field_icons,
      label_position: labelPosition ?? defaults.settings.label_position,
      ...(defaults.team_emails.length ? { emails: { team: [...defaults.team_emails], others: [], others_personal: false, receipt_field: null } } : {}),
    }
    const theme = form.template_key ? null : themeForNewForm(tenant, defaults.theme_id)
    if (theme) {
      form.schema.theme = theme.tokens
      form.schema.theme_id = theme.id
    }
    if (defaults.thank_you.title || defaults.thank_you.message) form.schema.thank_you = { ...form.schema.thank_you, ...(defaults.thank_you.title ? { title: defaults.thank_you.title } : {}), ...(defaults.thank_you.message ? { message: defaults.thank_you.message } : {}) }
  }
  if (defaults.embed_domains.length) form.embed_domains = [...defaults.embed_domains]
}

export const createForm = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(createSchema, body)
  if (input.template_key && !schemaForTemplate(tenant, input.template_key))
    throw new MockError('FRM-GEN-1002', [{ field: 'template_key', message: 'Choose a template from the gallery.' }])
  const form = newForm(tenant, user, { ...input, folder: folderRef(tenant, input.folder_id) })
  withFormDefaults(tenant, form, input.label_position)
  saveForms()
  audit(event, tenant, user, 'forms.created', form, [], {
    source: input.template_key ? 'template' : 'blank',
    ...(input.template_key ? { template: input.template_key } : {}),
  })
  return ok(summaryOf(form), {}, 201)
})

export const importForm = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(importSchema, body)
  const form = newForm(tenant, user, { ...input, folder: folderRef(tenant, input.folder_id) })
  audit(event, tenant, user, 'forms.created', form, [], { source: 'import' })
  return ok(summaryOf(form), {}, 201)
})

export const duplicateForm = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const source = findForm(tenant, user, getRouterParam(event, 'id'), { need: 'edit' })
  const copy = newForm(tenant, user, {
    name: `${source.name} (copy)`.slice(0, 120),
    folder: source.folder,
    template_key: source.template_key,
    schema: source.schema ? structuredClone(source.schema) : null,
  })
  copy.tags = [...source.tags]
  audit(event, tenant, user, 'forms.created', copy, [], { source: 'duplicate', from: source.name })
  return ok(summaryFor(copy, user), {}, 201)
})

// ── Change ────────────────────────────────────────────────────────────────────────

const patchSchema = z.object({
  row_version: z.number().int(),
  name: name.optional(),
  folder_id: z.string().nullable().optional(),
  tags: z
    .array(
      z
        .string()
        .trim()
        .toLowerCase()
        .min(1)
        .max(30)
        .regex(/^[\p{L}\p{N} _-]+$/u, 'Letters, numbers, spaces, - and _.'),
    )
    .max(20)
    .optional(),
  /** Availability (F10): ISO date-times or null for no limit. */
  opens_at: z.iso.datetime({ offset: true }).nullable().optional(),
  closes_at: z.iso.datetime({ offset: true }).nullable().optional(),
})

export const patchForm = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const form = findForm(tenant, user, getRouterParam(event, 'id'))
  const input = parseBody(patchSchema, body)
  checkVersion(form, input.row_version)
  const changes: AuditChange[] = []
  if (input.name !== undefined && input.name !== form.name) {
    changes.push({ field: 'name', before: form.name, after: input.name })
    form.name = input.name
  }
  if (input.folder_id !== undefined && input.folder_id !== (form.folder?.id ?? null)) {
    const folder = folderRef(tenant, input.folder_id)
    changes.push({ field: 'folder', before: form.folder?.name ?? null, after: folder?.name ?? null })
    form.folder = folder
  }
  for (const field of ['opens_at', 'closes_at'] as const) {
    const value = input[field]
    if (value === undefined || value === form[field]) continue
    changes.push({ field, before: form[field], after: value })
    form[field] = value
  }
  if (form.opens_at && form.closes_at && Date.parse(form.closes_at) <= Date.parse(form.opens_at))
    throw new MockError('FRM-GEN-1002', [{ field: 'closes_at', message: 'Choose an end after the start.' }])
  if (input.tags !== undefined) {
    const tags = [...new Set(input.tags)].sort()
    if (tags.join(',') !== form.tags.join(',')) {
      changes.push({ field: 'tags', before: form.tags.join(', ') || null, after: tags.join(', ') || null })
      form.tags = tags
    }
  }
  if (changes.length) {
    touch(form)
    audit(event, tenant, user, 'forms.updated', form, changes)
  }
  return ok(summaryOf(form))
})

const TRANSITIONS: Record<
  Exclude<FormLifecycleAction, 'restore'>,
  { from: FormStatus[]; action: AuditAction }
> = {
  unpublish: { from: ['published'], action: 'forms.unpublished' },
  close: { from: ['published'], action: 'forms.closed' },
  reopen: { from: ['closed'], action: 'forms.reopened' },
  archive: { from: ['draft', 'published', 'closed'], action: 'forms.archived' },
  unarchive: { from: ['archived'], action: 'forms.unarchived' },
}

function applyLifecycle(form: StoredForm, action: FormLifecycleAction): AuditChange[] {
  if (action === 'restore') {
    if (!form.deleted_at) throw new MockError('FRM-FORM-1007')
    form.deleted_at = null
    return []
  }
  const rule = TRANSITIONS[action]
  if (form.deleted_at || !rule.from.includes(form.status)) throw new MockError('FRM-FORM-1007')
  const before = form.status
  form.status =
    action === 'unpublish'
      ? 'draft'
      : action === 'close'
        ? 'closed'
        : action === 'reopen'
          ? 'published'
          : action === 'archive'
            ? 'archived'
            : (form.previous_status ?? 'draft')
  form.previous_status = action === 'archive' ? before : null
  return [{ field: 'status', before, after: form.status }]
}

const lifecycleSchema = z.object({ row_version: z.number().int().optional() })
const LIFECYCLE_ACTIONS = ['unpublish', 'close', 'reopen', 'archive', 'unarchive', 'restore'] as const

/** POST /forms/:id/:action, unpublish · close · reopen · archive · unarchive · restore (from Trash). */
export const formLifecycle = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const action = getRouterParam(event, 'action') as FormLifecycleAction
  if (!LIFECYCLE_ACTIONS.includes(action)) throw new MockError('FRM-GEN-1004')
  const form = findForm(tenant, user, getRouterParam(event, 'id'), { trash: action === 'restore' })
  checkVersion(form, parseBody(lifecycleSchema, body ?? {}).row_version)
  const changes = applyLifecycle(form, action)
  touch(form)
  audit(
    event,
    tenant,
    user,
    action === 'restore' ? 'forms.restored' : TRANSITIONS[action].action,
    form,
    changes,
  )
  return ok(summaryOf(form))
})

/** A form deleted for good: its short link code is never handed out again (data/shortCodeStore.ts). */
const retireCodesOf = (form: StoredForm) => form.short_code && retireShortCode(form.short_code)

/** DELETE /forms/:id → Trash; `?permanent=1` on a form already in Trash removes it for good. */
export const deleteForm = defineMockRoute(({ event, query }) => {
  const { user, tenant } = requireAuth(event)
  const id = getRouterParam(event, 'id')
  const store = formsOf(tenant)
  if (query.permanent === '1') {
    const form = findForm(tenant, user, id, { trash: true })
    retireCodesOf(form)
    store.forms = store.forms.filter(item => item.id !== form.id)
    saveForms()
    audit(event, tenant, user, 'forms.purged', form)
    return ok({ deleted: true })
  }
  const form = findForm(tenant, user, id)
  form.deleted_at = new Date().toISOString()
  touch(form)
  audit(event, tenant, user, 'forms.deleted', form, [], { kept_in_trash: '30 days' })
  return ok(summaryOf(form))
})

/**
 * DELETE /forms/trash, empty the Trash: only the forms this person can edit (people access,
 * decision 97); the others stay and are counted in `skipped`.
 */
export const emptyTrash = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const store = formsOf(tenant)
  const trashed = store.forms.filter(form => form.deleted_at && levelOf(form, user) === 'edit')
  const skipped = store.forms.filter(form => form.deleted_at && canSee(form, user) && levelOf(form, user) !== 'edit').length
  trashed.forEach(retireCodesOf)
  const gone = new Set(trashed)
  store.forms = store.forms.filter(form => !gone.has(form))
  saveForms()
  for (const form of trashed) audit(event, tenant, user, 'forms.purged', form, [], { via: 'empty_trash' })
  return ok({ deleted: trashed.length, skipped })
})

const bulkSchema = z.object({
  action: z.enum(['archive', 'move', 'delete', 'restore', 'purge']),
  ids: z.array(z.string()).min(1).max(100),
  folder_id: z.string().nullable().optional(),
})

/** POST /forms/bulk, one result per form; a form that can't take the action is reported, not fatal. */
export const bulkForms = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(bulkSchema, body)
  const store = formsOf(tenant)
  const folder = input.action === 'move' ? folderRef(tenant, input.folder_id) : null
  const result: FormBulkResult = { updated: 0, failed: [] }
  for (const id of input.ids) {
    try {
      const inTrash = input.action === 'restore' || input.action === 'purge'
      const form = findForm(tenant, user, id, { trash: inTrash })
      if (input.action === 'move') {
        if ((form.folder?.id ?? null) !== (folder?.id ?? null)) {
          const change = { field: 'folder', before: form.folder?.name ?? null, after: folder?.name ?? null }
          form.folder = folder
          touch(form)
          audit(event, tenant, user, 'forms.updated', form, [change], { via: 'bulk' })
        }
      } else if (input.action === 'delete') {
        form.deleted_at = new Date().toISOString()
        touch(form)
        audit(event, tenant, user, 'forms.deleted', form, [], { via: 'bulk' })
      } else if (input.action === 'purge') {
        retireCodesOf(form)
        store.forms = store.forms.filter(item => item.id !== form.id)
        audit(event, tenant, user, 'forms.purged', form, [], { via: 'bulk' })
      } else {
        const changes = applyLifecycle(form, input.action)
        touch(form)
        audit(
          event,
          tenant,
          user,
          input.action === 'restore' ? 'forms.restored' : 'forms.archived',
          form,
          changes,
          {
            via: 'bulk',
          },
        )
      }
      result.updated++
    } catch (error) {
      result.failed.push({ id, code: error instanceof MockError ? error.code : 'FRM-GEN-5000' })
    }
  }
  saveForms()
  return ok(result)
})

// ── Folders ───────────────────────────────────────────────────────────────────────

const folderSchema = z.object({
  name: z.string().trim().min(1, 'Give the folder a name.').max(60),
  /** Icon colour (F11 M4): a key of FOLDER_COLORS, or any custom colour as #rrggbb. */
  color: z.union([z.enum(FOLDER_COLOR_KEYS as [FolderColor, ...FolderColor[]]), z.string().regex(/^#[0-9a-fA-F]{6}$/)]).optional(),
})

function assertFolderName(tenant: MockTenant, folderName: string, exceptId?: string) {
  const taken = formsOf(tenant).folders.some(
    folder => folder.id !== exceptId && folder.name.toLowerCase() === folderName.toLowerCase(),
  )
  if (taken)
    throw new MockError('FRM-FORM-1008', [{ field: 'name', message: 'A folder with this name exists.' }])
}

const folderAudit = (
  event: H3Event,
  tenant: MockTenant,
  user: MockUser,
  action: AuditAction,
  folder: FormFolder,
  changes: AuditChange[] = [],
) =>
  recordAudit(event, tenant, {
    action,
    actor: actorOf(user),
    resource: { type: 'folder', id: folder.id, name: folder.name },
    changes,
  })

/** GET /folders, with the number of forms in each (Trash not counted). */
export const listFolders = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const store = formsOf(tenant)
  return ok(
    store.folders
      .map(folder => ({
        ...folder,
        // Only forms this person can see (people access): hidden forms don't show up as numbers either.
        // Archived forms are not counted, like the forms list and the sidebar.
        forms_count: store.forms.filter(form => !form.deleted_at && form.status !== 'archived' && form.folder?.id === folder.id && inScope(tenant, form) && canSee(form, user)).length,
      }))
      .sort((a, b) => a.name.localeCompare(b.name)),
  )
})

export const createFolder = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const { name: folderName, color } = parseBody(folderSchema, body)
  assertFolderName(tenant, folderName)
  const folder: FormFolder = { id: crypto.randomUUID(), name: folderName, color: color ?? 'ink' }
  formsOf(tenant).folders.push(folder)
  saveForms()
  folderAudit(event, tenant, user, 'forms.folder_created', folder)
  return ok({ ...folder, forms_count: 0 }, {}, 201)
})

export const renameFolder = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const store = formsOf(tenant)
  const folder = store.folders.find(item => item.id === getRouterParam(event, 'id'))
  if (!folder) throw new MockError('FRM-GEN-1004')
  // PATCH: the name, the colour, or both (F11 M4).
  const input = parseBody(folderSchema.partial(), body)
  const folderName = input.name ?? folder.name
  assertFolderName(tenant, folderName, folder.id)
  const before = folder.name
  const beforeColor = folder.color ?? 'ink'
  folder.name = folderName
  if (input.color) folder.color = input.color
  for (const form of store.forms)
    if (form.folder?.id === folder.id) form.folder = { id: folder.id, name: folderName, color: folder.color ?? null }
  saveForms()
  const changes = [
    ...(before !== folderName ? [{ field: 'name', before, after: folderName }] : []),
    ...(input.color && input.color !== beforeColor ? [{ field: 'colour', before: beforeColor, after: input.color }] : []),
  ]
  if (changes.length) folderAudit(event, tenant, user, 'forms.folder_renamed', folder, changes)
  return ok(folder)
})

/** DELETE /folders/:id, only empty folders (forms in Trash just lose the folder). */
export const deleteFolder = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const store = formsOf(tenant)
  const folder = store.folders.find(item => item.id === getRouterParam(event, 'id'))
  if (!folder) throw new MockError('FRM-GEN-1004')
  const holding = store.forms.filter(form => !form.deleted_at && form.folder?.id === folder.id).length
  if (holding) throw new MockError('FRM-FORM-1013', [{ field: 'folder', message: `${holding} forms` }])
  store.folders = store.folders.filter(item => item.id !== folder.id)
  let moved = 0
  for (const form of store.forms)
    if (form.folder?.id === folder.id) {
      form.folder = null
      moved++
    }
  saveForms()
  recordAudit(event, tenant, {
    action: 'forms.folder_deleted',
    actor: actorOf(user),
    resource: { type: 'folder', id: folder.id, name: folder.name },
    metadata: { forms_moved_out: String(moved) },
  })
  return ok({ deleted: true, forms_moved_out: moved })
})
