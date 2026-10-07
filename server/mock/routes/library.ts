/**
 * Mock reusable building blocks (docs/API-CONTRACT.md → Field library & option lists):
 * saved fields, per workspace (option lists: ./optionLists.ts). Every change is in the audit trail.
 */
import { z } from 'zod'
import { formFieldSchema } from '#shared/utils/forms/schema'
import { requireAuth } from '../core/auth'
import { actorOf, recordAudit } from '../core/audit'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { libraryOf, saveLibrary } from '../data/libraryStore'

const name = z.string().trim().min(1).max(80)
const savedFieldBody = z.object({ name, field: formFieldSchema.omit({ id: true }) })

/** Who made it, name only, never the email. */
const authorOf = (user: Parameters<typeof actorOf>[0]) => {
  const { id, name: fullName } = actorOf(user)
  return { id: id ?? user.id, name: fullName ?? '' }
}
const byName = <T extends { name: string }>(items: T[]) =>
  [...items].sort((a, b) => a.name.localeCompare(b.name))

// ── Saved fields ──────────────────────────────────────────────────────────────────────
export const listSavedFields = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  return ok(byName(libraryOf(tenant).fields))
})

export const saveField = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(savedFieldBody, body)
  const store = libraryOf(tenant)
  if (store.fields.length >= 500) throw new MockError('FRM-GEN-1002', [{ field: 'name', message: 'Library is full.' }])
  const saved = { id: crypto.randomUUID(), name: input.name, field: input.field, created_by: authorOf(user), created_at: new Date().toISOString() }
  store.fields.push(saved)
  saveLibrary()
  recordAudit(event, tenant, {
    action: 'forms.field_saved',
    actor: actorOf(user),
    resource: { type: 'saved_field', id: saved.id, name: saved.name },
    metadata: { field_type: input.field.type },
  })
  return ok(saved, {}, 201)
})

export const deleteSavedField = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const store = libraryOf(tenant)
  const index = store.fields.findIndex(item => item.id === getRouterParam(event, 'id'))
  if (index < 0) throw new MockError('FRM-GEN-1004')
  const [removed] = store.fields.splice(index, 1)
  saveLibrary()
  recordAudit(event, tenant, {
    action: 'forms.field_removed',
    actor: actorOf(user),
    resource: { type: 'saved_field', id: removed!.id, name: removed!.name },
  })
  return ok({ id: removed!.id })
})
