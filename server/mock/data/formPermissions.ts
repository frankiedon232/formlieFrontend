/**
 * Who may do what with a form (F10 M3 people access, decision 97; F22 R2 granular roles with scope,
 * owner 2026-10-10). One answer for every route and every list:
 *
 *   1. Folder access: a form in a folder the person may not see doesn't exist for them (lists, counts,
 *      search, responses, exports …). Owner, people who decide folder access, and those the folder is
 *      open to (roles, departments, people) see it.
 *   2. The role's grant for the action (forms.rename, forms.publish …) and its scope:
 *        own     the person made the form
 *        shared  own, or the form is shared with them at the level the action needs (people access:
 *                their own level, else the form's team default)
 *        all     every form
 *      No grant: not even their own. Form sharing never goes beyond the role.
 *
 * `levelOf` (none < responses < view < edit) stays for the response routes until responses get their own
 * scopes. Too little → FRM-PERM-1001; can't see → FRM-GEN-1004, so a name never leaks.
 */
import { FORM_ACTIONS, RESPONSE_ACTIONS, type FolderActions, type FormAccessLevel, type FormAction, type FormActions, type FormFolder, type ResponseAction, type ResponseActions } from '#shared/types/forms'
import { MockError } from '../core/respond'
import type { StoredForm } from './formStore'
import { formsOf, summaryOf } from './formStore'
import { orgOf } from './orgStore'
import { can, scopeOf } from './rolesStore'
import { MOCK_TENANTS, type MockTenant, type MockUser } from './tenants'

const RANK: Record<FormAccessLevel, number> = { none: 0, responses: 1, view: 2, edit: 3 }

export interface FormGrant {
  user_id: string
  level: Exclude<FormAccessLevel, 'none'>
  granted_at: string
}

/** The sharing level an action needs when the role reaches "shared" forms. */
const LEVEL_FOR: Record<FormAction, Exclude<FormAccessLevel, 'none'>> = {
  view: 'responses',
  preview: 'view',
  share_view: 'view',
  duplicate: 'view',
  save_template: 'edit',
  rename: 'edit',
  edit: 'edit',
  versions: 'edit',
  share: 'edit',
  availability: 'edit',
  publish: 'edit',
  close: 'edit',
  archive: 'edit',
  move: 'edit',
  delete: 'edit',
  purge: 'edit',
}

const tenantOfUser = (user: MockUser) => MOCK_TENANTS.find(item => item.id === user.tenant_id)

/** Every form, not only those shared with them (forms.view at scope All). */
export const isWorkspaceAdmin = (user: MockUser) => scopeOf(user, 'forms.view') === 'all'

// ── Folders ───────────────────────────────────────────────────────────────────────

/** True when this person may see the folder (and so the forms in it). */
export function folderVisible(folder: FormFolder | null | undefined, user: MockUser, tenant = tenantOfUser(user)): boolean {
  const access = folder?.access
  if (!access?.restricted) return true
  if (user.role === 'owner' || can(user, 'folders.access', tenant)) return true
  if (access.people.includes(user.id) || access.roles.includes(user.role)) return true
  if (!tenant || !access.departments.length) return false
  return orgOf(tenant).departments.some(item => access.departments.includes(item.id) && item.member_ids.includes(user.id))
}

/** The folder as stored (a form only carries its id and name). */
const folderOf = (form: StoredForm, tenant: MockTenant | undefined) => (form.folder && tenant ? (formsOf(tenant).folders.find(item => item.id === form.folder!.id) ?? null) : null)

// ── Forms ─────────────────────────────────────────────────────────────────────────

/** The level the form is shared with this person (their own, else the team default; the maker: edit). */
function sharedLevel(form: StoredForm, user: MockUser): FormAccessLevel {
  if (form.owner?.id === user.id) return 'edit'
  return (form.grants ?? []).find(item => item.user_id === user.id)?.level ?? form.team_access ?? 'edit'
}

/** May this person take this action on this form? */
export function allows(form: StoredForm, user: MockUser, action: FormAction, tenant = tenantOfUser(user)): boolean {
  if (!folderVisible(folderOf(form, tenant), user, tenant)) return false
  const scope = scopeOf(user, `forms.${action}`, tenant)
  if (!scope) return false
  if (scope === 'all') return true
  if (form.owner?.id === user.id) return true
  return scope === 'shared' && RANK[sharedLevel(form, user)] >= RANK[LEVEL_FOR[action]]
}

/** Everything this person may do with this form (sent with every form, so the app shows only that). */
export const actionsOf = (form: StoredForm, user: MockUser, tenant = tenantOfUser(user)): FormActions =>
  Object.fromEntries(FORM_ACTIONS.map(action => [action, allows(form, user, action, tenant)])) as FormActions

/** Allowed, else refused: a form they can't see stays "not found"; one they see but may not change says so. */
export function requireAction(form: StoredForm, user: MockUser, action: FormAction, tenant = tenantOfUser(user)) {
  if (!allows(form, user, 'view', tenant)) throw new MockError('FRM-GEN-1004')
  if (!allows(form, user, action, tenant)) throw new MockError('FRM-PERM-1001')
}

/** This person's level on this form, for the response routes (none < responses < view < edit). */
export function levelOf(form: StoredForm, user: MockUser): FormAccessLevel {
  const tenant = tenantOfUser(user)
  if (!allows(form, user, 'view', tenant)) return 'none'
  if (allows(form, user, 'edit', tenant)) return 'edit'
  if (allows(form, user, 'preview', tenant)) return 'view'
  return 'responses'
}

export const canSee = (form: StoredForm, user: MockUser) => allows(form, user, 'view')

/** At least this level, else refused (a form they may not see at all stays "not found"). */
export function requireLevel(form: StoredForm, user: MockUser, needed: Exclude<FormAccessLevel, 'none'>): FormAccessLevel {
  const level = levelOf(form, user)
  if (level === 'none') throw new MockError('FRM-GEN-1004')
  if (RANK[level] < RANK[needed]) throw new MockError('FRM-PERM-1001')
  return level
}

/** What this person may do with a folder they can see: change it (own · all), delete it, decide who sees it. */
export function folderActions(folder: FormFolder, user: MockUser, tenant = tenantOfUser(user)): FolderActions {
  const reach = (permission: 'folders.edit' | 'folders.delete') => {
    const scope = scopeOf(user, permission, tenant)
    return scope === 'all' || (scope === 'own' && folder.created_by?.id === user.id)
  }
  return { edit: reach('folders.edit'), delete: reach('folders.delete'), access: can(user, 'folders.access', tenant) }
}

/** A folder as the app gets it: without who it is open to unless the person decides that. */
export function folderFor(folder: FormFolder, user: MockUser, tenant = tenantOfUser(user)): FormFolder {
  const actions = folderActions(folder, user, tenant)
  const { access, ...rest } = folder
  return { ...rest, ...(actions.access ? { access: access ?? { restricted: false, roles: [], departments: [], people: [] } } : { access: access?.restricted ? { restricted: true, roles: [], departments: [], people: [] } : null }), can: actions }
}

/** A form summary with what this person may do (my_access for the response pages, can for everything else). */
export const summaryFor = (form: StoredForm, user: MockUser) => ({ ...summaryOf(form), my_access: levelOf(form, user), can: actionsOf(form, user), responses_can: responseActionsOf(form, user) })

// ── Responses (F22 R2 M2) ─────────────────────────────────────────────────────────

/** The sharing level each response action needs when the role reaches "shared" forms. */
const RESPONSE_LEVEL: Record<ResponseAction, Exclude<FormAccessLevel, 'none'>> = { view: 'responses', review: 'responses', export: 'responses', edit: 'edit', delete: 'edit' }

/**
 * May this person take this action on the responses of this form? The folder must be visible; then the
 * role's grant for responses.<action> and its scope: own (they made the form) · shared (also forms
 * shared with them at the level the action needs) · all.
 */
export function responsesAllowed(form: StoredForm, user: MockUser, action: ResponseAction, tenant = tenantOfUser(user)): boolean {
  if (!folderVisible(folderOf(form, tenant), user, tenant)) return false
  const scope = scopeOf(user, `responses.${action}`, tenant)
  if (!scope) return false
  if (scope === 'all' || form.owner?.id === user.id) return true
  return scope === 'shared' && RANK[sharedLevel(form, user)] >= RANK[RESPONSE_LEVEL[action]]
}

/** Every response action this person may take on this form (sent with forms and responses). */
export const responseActionsOf = (form: StoredForm, user: MockUser, tenant = tenantOfUser(user)): ResponseActions =>
  Object.fromEntries(RESPONSE_ACTIONS.map(action => [action, responsesAllowed(form, user, action, tenant)])) as ResponseActions

/** Allowed, else refused: responses they can't see stay "not found". */
export function requireResponses(form: StoredForm, user: MockUser, action: ResponseAction, tenant = tenantOfUser(user)) {
  if (!responsesAllowed(form, user, 'view', tenant)) throw new MockError('FRM-GEN-1004')
  if (!responsesAllowed(form, user, action, tenant)) throw new MockError('FRM-PERM-1001')
}
