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
  /** Their photo (My profile), a small data URL, or null. */
  photo: string | null
  role: WorkspaceRole
  /** The role's name (Roles & access). */
  role_name: string
  /** The role manages the workspace (people, settings or roles): two-step sign-in matters most. */
  privileged: boolean
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
  /** An invitation not yet accepted (F16 M2): when it ends and who sent it. */
  invite: { expires_at: string; sent_at: string; invited_by: string; expired: boolean } | null
}

/** POST /people/invites */
export interface InviteRequest {
  emails: string[]
  /** Any role id but owner (Roles & access). */
  role: string
  department_ids: string[]
  job_title_ids: string[]
  message?: string | null
}
export interface InviteResult {
  invited: number
  /** Addresses left out: already in the workspace, or already invited. */
  skipped: { email: string; reason: 'member' | 'invited' }[]
}

/** GET /public/invites/{token}: what the invitation page shows. */
export interface InvitePreview {
  workspace: string
  email: string
  inviter: string
  role: string
  role_name: string
  message: string | null
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
  /** Their five most recently changed forms (`forms_count` has them all). */
  forms: { id: string; name: string; status: string }[]
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

/** A role (Roles & access, F22): what its holders may do (GET /roles). */
export interface RoleRow {
  id: string
  name: string
  description: string | null
  permissions: string[]
  /** owner · admin · member for the built-in ones (Owner can't be changed), null for the workspace's own. */
  built_in: 'owner' | 'admin' | 'member' | null
  people_count: number
  /** A few of the people who hold it (avatars). */
  people: { id: string; name: string; photo: string | null }[]
  created_at: string
  updated_at: string
}

/** GET /roles/insights: the two cards on top of the Roles page. */
export interface RolesInsights {
  total: number
  custom: number
  people: number
  /** People per role, most first. */
  by_role: { id: string; name: string; count: number }[]
  /** How much of the platform each role opens (share of all permissions), for the lines card. */
  reach: { id: string; name: string; share: number }[]
}
