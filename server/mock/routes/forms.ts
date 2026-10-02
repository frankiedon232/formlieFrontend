/**
 * Mock forms + folders (docs/API-CONTRACT.md → Forms). Every change bumps `row_version`
 * (mismatch → FRM-GEN-1009) and is recorded in the audit trail with before / after values.
 */
import type { H3Event } from 'h3'
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
import { STARTER_TEMPLATE_KEYS } from '#shared/utils/templates/starters'
import type { AuditAction } from '#shared/utils/audit/events'
import { requireAuth } from '../core/auth'
import { actorOf, recordAudit } from '../core/audit'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { formsOf, saveForms, summaryOf, uniqueSlug, type StoredForm } from '../data/formStore'
import type { MockTenant, MockUser } from '../data/tenants'

type Query = Record<string, unknown>
const list = (query: Query, key: string) => {
  const value = query[`filter[${key}]`]
  return typeof value === 'string' && value ? value.split(',') : null
}
const day = (value: unknown, end: boolean) =>
  typeof value === 'string' && value ? Date.parse(`${value}T${end ? '23:59:59' : '00:00:00'}Z`) : null

function findForm(tenant: MockTenant, id: string | undefined, { trash = false } = {}): StoredForm {
  const form = formsOf(tenant).forms.find(item => item.id === id)
  if (!form || !!form.deleted_at !== trash) throw new MockError('FRM-GEN-1004')
  return form
}

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

/** GET /forms — filters: status, folder_id (`none` = no folder), owner_id, tag (comma = any of), trash=1; from/to on updated_at. */
export const listForms = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAuth(event)
  const status = list(query, 'status')
  const folder = list(query, 'folder_id')
  const owner = list(query, 'owner_id')
  const tag = list(query, 'tag')
  const trash = query['filter[trash]'] === '1'
  const from = day(query.from, false)
  const to = day(query.to, true)

  const filtered = formsOf(tenant).forms.filter(form => {
    const updated = Date.parse(form.updated_at)
    return (
      !!form.deleted_at === trash &&
      // Archived forms only show when asked for explicitly (and always in Trash).
      (trash || (status ? status.includes(form.status) : form.status !== 'archived')) &&
      (!folder || folder.includes(form.folder?.id ?? 'none')) &&
      (!owner || owner.includes(form.owner.id)) &&
      (!tag || form.tags.some(t => tag.includes(t))) &&
      (from === null || updated >= from) &&
      (to === null || updated <= to)
    )
  })

  const { data, meta } = paginate<StoredForm>(
    filtered,
    { sort: trash ? '-deleted_at' : '-updated_at', ...query },
    (form, q) => form.name.toLowerCase().includes(q) || form.slug.includes(q) || form.tags.includes(q),
  )
  return ok(data.map(summaryOf), meta)
})

export const formFacets = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const forms = formsOf(tenant).forms.filter(form => !form.deleted_at)
  const owners = new Map(forms.map(form => [form.owner.id, form.owner]))
  return ok<FormFacets>({
    owners: [...owners.values()].sort((a, b) => a.name.localeCompare(b.name)),
    tags: [...new Set(forms.flatMap(form => form.tags))].sort(),
  })
})

export const getForm = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const form = formsOf(tenant).forms.find(item => item.id === getRouterParam(event, 'id'))
  if (!form) throw new MockError('FRM-GEN-1004')
  return ok({ ...summaryOf(form), template_key: form.template_key, schema: form.schema })
})

// ── Create ────────────────────────────────────────────────────────────────────────

const name = z.string().trim().min(1, 'Give the form a name.').max(120)
const createSchema = z.object({
  name,
  folder_id: z.string().nullable().optional(),
  template_key: z
    .enum(STARTER_TEMPLATE_KEYS as [string, ...string[]])
    .nullable()
    .optional(),
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
  },
): StoredForm {
  const store = formsOf(tenant)
  const now = new Date().toISOString()
  const form: StoredForm = {
    id: crypto.randomUUID(),
    name: input.name,
    slug: uniqueSlug(store, input.name),
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
    schema: input.schema ?? null,
    template_key: input.template_key ?? null,
  }
  store.forms.unshift(form)
  saveForms()
  return form
}

export const createForm = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(createSchema, body)
  const form = newForm(tenant, user, { ...input, folder: folderRef(tenant, input.folder_id) })
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
  const source = findForm(tenant, getRouterParam(event, 'id'))
  const copy = newForm(tenant, user, {
    name: `${source.name} (copy)`.slice(0, 120),
    folder: source.folder,
    template_key: source.template_key,
    schema: source.schema ? structuredClone(source.schema) : null,
  })
  copy.tags = [...source.tags]
  audit(event, tenant, user, 'forms.created', copy, [], { source: 'duplicate', from: source.name })
  return ok(summaryOf(copy), {}, 201)
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
})

export const patchForm = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const form = findForm(tenant, getRouterParam(event, 'id'))
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

/** POST /forms/:id/:action — unpublish · close · reopen · archive · unarchive · restore (from Trash). */
export const formLifecycle = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const action = getRouterParam(event, 'action') as FormLifecycleAction
  if (!LIFECYCLE_ACTIONS.includes(action)) throw new MockError('FRM-GEN-1004')
  const form = findForm(tenant, getRouterParam(event, 'id'), { trash: action === 'restore' })
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

/** DELETE /forms/:id → Trash; `?permanent=1` on a form already in Trash removes it for good. */
export const deleteForm = defineMockRoute(({ event, query }) => {
  const { user, tenant } = requireAuth(event)
  const id = getRouterParam(event, 'id')
  const store = formsOf(tenant)
  if (query.permanent === '1') {
    const form = findForm(tenant, id, { trash: true })
    store.forms = store.forms.filter(item => item.id !== form.id)
    saveForms()
    audit(event, tenant, user, 'forms.purged', form)
    return ok({ deleted: true })
  }
  const form = findForm(tenant, id)
  form.deleted_at = new Date().toISOString()
  touch(form)
  audit(event, tenant, user, 'forms.deleted', form, [], { kept_in_trash: '30 days' })
  return ok(summaryOf(form))
})

/** DELETE /forms/trash — empty the Trash. */
export const emptyTrash = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const store = formsOf(tenant)
  const trashed = store.forms.filter(form => form.deleted_at)
  store.forms = store.forms.filter(form => !form.deleted_at)
  saveForms()
  for (const form of trashed) audit(event, tenant, user, 'forms.purged', form, [], { via: 'empty_trash' })
  return ok({ deleted: trashed.length })
})

const bulkSchema = z.object({
  action: z.enum(['archive', 'move', 'delete', 'restore', 'purge']),
  ids: z.array(z.string()).min(1).max(100),
  folder_id: z.string().nullable().optional(),
})

/** POST /forms/bulk — one result per form; a form that can't take the action is reported, not fatal. */
export const bulkForms = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(bulkSchema, body)
  const store = formsOf(tenant)
  const folder = input.action === 'move' ? folderRef(tenant, input.folder_id) : null
  const result: FormBulkResult = { updated: 0, failed: [] }
  for (const id of input.ids) {
    try {
      const inTrash = input.action === 'restore' || input.action === 'purge'
      const form = findForm(tenant, id, { trash: inTrash })
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

const folderSchema = z.object({ name: z.string().trim().min(1, 'Give the folder a name.').max(60) })

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

/** GET /folders — with the number of forms in each (Trash not counted). */
export const listFolders = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const store = formsOf(tenant)
  return ok(
    store.folders
      .map(folder => ({
        ...folder,
        forms_count: store.forms.filter(form => !form.deleted_at && form.folder?.id === folder.id).length,
      }))
      .sort((a, b) => a.name.localeCompare(b.name)),
  )
})

export const createFolder = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const { name: folderName } = parseBody(folderSchema, body)
  assertFolderName(tenant, folderName)
  const folder: FormFolder = { id: crypto.randomUUID(), name: folderName }
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
  const { name: folderName } = parseBody(folderSchema, body)
  assertFolderName(tenant, folderName, folder.id)
  const before = folder.name
  folder.name = folderName
  for (const form of store.forms)
    if (form.folder?.id === folder.id) form.folder = { id: folder.id, name: folderName }
  saveForms()
  if (before !== folderName)
    folderAudit(event, tenant, user, 'forms.folder_renamed', folder, [
      { field: 'name', before, after: folderName },
    ])
  return ok(folder)
})

/** DELETE /folders/:id — its forms stay, without a folder. */
export const deleteFolder = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const store = formsOf(tenant)
  const folder = store.folders.find(item => item.id === getRouterParam(event, 'id'))
  if (!folder) throw new MockError('FRM-GEN-1004')
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
