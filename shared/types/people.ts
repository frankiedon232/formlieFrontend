/**
 * People of a workspace (F16 Users & profiles, owner 2026-10-08: profile and users are one thing). Each
 * person is profiled with departments and job titles (from Settings → Organisation data) and one role
 * (Owner, Admin, Member until F22 adds custom roles; the role decides access, RBAC).
 */
import type { WorkspaceRole } from './auth'

/**
 * active · not_activated (a profile an admin made; the activation email is out) · invited (a personal
 * sign-up link is out) · pending (signed up with a link, awaiting approval) · disabled.
 */
export type PersonStatus = 'active' | 'not_activated' | 'invited' | 'pending' | 'disabled'
export const PERSON_STATUSES: PersonStatus[] = ['active', 'not_activated', 'invited', 'pending', 'disabled']
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
  /** The latest visit (a sign-in session, else a run of activity in the audit trail): when it started and ended, and whether they're online now. */
  last_visit: { started_at: string; ended_at: string; online: boolean } | null
  joined_at: string
  /** Forms this person owns. */
  forms_count: number
  /** An invitation not yet accepted (F16 M2): when it ends and who sent it. */
  invite: { kind: 'invite' | 'activation'; expires_at: string; sent_at: string; invited_by: string; expired: boolean } | null
  /** Signed up with a link and waiting for approval: how (personal link or the workspace's link) and when. */
  request: { via: 'invite' | 'link'; at: string } | null
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

/**
 * GET /public/invites/{token}: what the sign-up page shows. `activation` = a profile an admin made (set a
 * password, then sign in); `invite` = a personal sign-up link; `link` = the workspace's shared link (both
 * wait for approval).
 */
export interface InvitePreview {
  kind: 'activation' | 'invite' | 'link'
  workspace: string
  email: string | null
  first_name: string
  last_name: string
  inviter: string | null
  role: string | null
  role_name: string | null
  message: string | null
  /** The shared link: email domains it accepts (empty = any). */
  domains: string[]
}

/** POST /people: a user profile made by an admin (activation email follows). */
export interface ProfileRequest {
  first_name: string
  last_name: string
  email: string
  phone: string | null
  role: string
  department_ids: string[]
  job_title_ids: string[]
  manager_id: string | null
}

/** GET /people/signup-link */
export interface SignupLinkView {
  enabled: boolean
  link: string
  domains: string[]
  updated_at: string
  pending: number
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
