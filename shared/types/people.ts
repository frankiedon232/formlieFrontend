/**
 * People of a workspace (F16 Users & profiles, owner 2026-10-08: profile and users are one thing). Each
 * person is profiled with departments and job titles (from Settings → Organisation data) and one role
 * (Owner, Admin, Member until F22 adds custom roles; the role decides access, RBAC).
 */
import type { WorkspaceRole } from './auth'

export type PersonStatus = 'active' | 'invited' | 'disabled'
export const PERSON_STATUSES: PersonStatus[] = ['active', 'invited', 'disabled']
export const WORKSPACE_ROLES: WorkspaceRole[] = ['owner', 'admin', 'member']

export interface PersonRef {
  id: string
  name: string
}

/** A row of the People page (GET /people). */
export interface PersonRow {
  id: string
  first_name: string
  last_name: string
  name: string
  email: string
  phone: string | null
  role: WorkspaceRole
  status: PersonStatus
  departments: PersonRef[]
  job_titles: PersonRef[]
  manager: PersonRef | null
  /** Two-step sign-in set up (authenticator app or SMS). */
  two_step: boolean
  last_active_at: string | null
  joined_at: string
  /** Forms this person owns. */
  forms_count: number
}

/** One person's detail panel (GET /people/{id}). */
export interface PersonDetail extends PersonRow {
  /** Where and how they last signed in. */
  last_sign_in: { at: string; city: string | null; country: string | null; browser: string | null; os: string | null } | null
  /** Sign-ins and other actions in the last 30 days (the audit trail keeps the history). */
  sign_ins_30d: number
  actions_30d: number
  /** People who report to them. */
  reports: PersonRef[]
}

/** GET /people/insights: the two cards on top of the People page. */
export interface PeopleInsights {
  total: number
  /** Joined in the last 30 days, and in the 30 before. */
  joined: number
  joined_previous: number
  two_step: number
  by_status: Record<PersonStatus, number>
  by_role: Record<WorkspaceRole, number>
  /** Sign-ins per day, last 30 days. */
  daily: { date: string; count: number }[]
}
