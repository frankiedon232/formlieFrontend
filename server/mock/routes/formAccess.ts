/**
 * Who can see this form (leftovers L4, owner 2026-10-10; docs/API-CONTRACT.md → Forms). Everyone active in the
 * workspace, with what they may do with the form and the first rule that decides it, worked out with the same
 * functions every route uses (formPermissions.ts), so the overview never disagrees with what really happens.
 * For people who may see the form's sharing (`forms.share_view`); read only, changes stay in Share → People.
 *
 *   GET /forms/:id/access → FormAccessOverview
 */
import type { AccessReason, FormAccessOverview } from '#shared/types/forms'
import { scopeParts } from '#shared/utils/auth/permissions'
import { requireAuth } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { folderVisible, levelOf, requireAction, responsesAllowed } from '../data/formPermissions'
import { formsOf, type StoredForm } from '../data/formStore'
import { accountOf, peopleStoreOf, type StoredPerson } from '../data/peopleStore'
import { roleOf, scopeOf } from '../data/rolesStore'
import type { MockTenant, MockUser } from '../data/tenants'

const RANK = { edit: 0, view: 1, responses: 2, none: 3 } as const

/** A person as the permission checks take them (their role from People, their account when they have one). */
const asUser = (person: StoredPerson, tenant: MockTenant): MockUser =>
  ({ ...(accountOf(person.id) ?? { first_name: person.first_name, last_name: person.last_name, email: person.email, password: '', phone: null, disabled: false }), id: person.id, role: person.role, tenant_id: tenant.id }) as MockUser

/** The first rule that decides this person's access, in the order the checks run. */
function reasonOf(form: StoredForm, user: MockUser, tenant: MockTenant): AccessReason {
  const folder = form.folder ? (formsOf(tenant).folders.find(item => item.id === form.folder!.id) ?? null) : null
  if (!folderVisible(folder, user, tenant)) return 'folder_hidden'
  const scope = scopeOf(user, 'forms.view', tenant)
  if (!scope) return 'role_none'
  const parts = scopeParts(scope)
  if (parts & 4) return user.role === 'owner' ? 'workspace_owner' : 'all_forms'
  if (form.owner?.id === user.id) return parts & 1 ? 'form_owner' : 'role_none'
  if (!(parts & 2)) return 'role_own_only'
  if ((form.grants ?? []).some(grant => grant.user_id === user.id)) return 'own_grant'
  return (form.team_access ?? 'edit') === 'none' ? 'not_shared' : 'team_default'
}

export const formAccess = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const form = formsOf(tenant).forms.find(item => item.id === getRouterParam(event, 'id') && !item.deleted_at)
  if (!form) throw new MockError('FRM-GEN-1004')
  requireAction(form, user, 'share_view', tenant)

  const people = peopleStoreOf(tenant)
    .filter(person => person.status === 'active')
    .map(person => {
      const account = asUser(person, tenant)
      return {
        user: { id: person.id, name: `${person.first_name} ${person.last_name}`.trim() || person.email, email: person.email, photo: person.photo ?? null },
        role: { id: person.role, name: roleOf(tenant, person.role)?.name ?? person.role },
        level: levelOf(form, account),
        responses: responsesAllowed(form, account, 'view', tenant),
        reason: reasonOf(form, account, tenant),
      }
    })
    .sort((a, b) => RANK[a.level] - RANK[b.level] || a.user.name.localeCompare(b.user.name))

  const folder = form.folder ? (formsOf(tenant).folders.find(item => item.id === form.folder!.id) ?? null) : null
  const result: FormAccessOverview = { folder: folder ? { id: folder.id, name: folder.name, restricted: !!folder.access?.restricted } : null, people }
  return ok(result)
})
