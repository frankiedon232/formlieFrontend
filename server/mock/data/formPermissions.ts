/**
 * People access per form (F10 M3, decision 97). One rule for every route:
 *   workspace owner / admin  → edit (always)
 *   the form's owner         → edit (always)
 *   a person given access    → their level (edit · view · responses), more or less than the default
 *   everyone else            → the form's team default (edit · view · none; default edit = as before)
 * Levels: none < responses (list, overview, responses) < view (also a read-only preview of the
 * form) < edit (everything: editor, logic, design, sharing, versions, templates, lifecycle).
 * Too little → FRM-PERM-1001; none → the form doesn't exist for them (FRM-GEN-1004), so its name
 * never leaks. Full roles & permissions come with F22.
 */
import type { FormAccessLevel } from '#shared/types/forms'
import { MockError } from '../core/respond'
import type { StoredForm } from './formStore'
import type { MockUser } from './tenants'
import { can } from './rolesStore'

const RANK: Record<FormAccessLevel, number> = { none: 0, responses: 1, view: 2, edit: 3 }

export interface FormGrant {
  user_id: string
  level: Exclude<FormAccessLevel, 'none'>
  granted_at: string
}

/** Every form, not only those shared with them (Roles & access: forms.all). */
export const isWorkspaceAdmin = (user: MockUser) => can(user, 'forms.all')

/** This person's level on this form. */
export function levelOf(form: StoredForm, user: MockUser): FormAccessLevel {
  if (isWorkspaceAdmin(user) || form.owner?.id === user.id) return 'edit'
  const grant = (form.grants ?? []).find(item => item.user_id === user.id)
  if (grant) return grant.level
  return form.team_access ?? 'edit'
}

export const canSee = (form: StoredForm, user: MockUser) => levelOf(form, user) !== 'none'

/** At least this level, else refused (a form they may not see at all stays "not found"). */
export function requireLevel(form: StoredForm, user: MockUser, needed: Exclude<FormAccessLevel, 'none'>): FormAccessLevel {
  const level = levelOf(form, user)
  if (level === 'none') throw new MockError('FRM-GEN-1004')
  if (RANK[level] < RANK[needed]) throw new MockError('FRM-PERM-1001')
  return level
}
