/**
 * Organisations in a workspace (F14 M7, owner 2026-10-07: shared team): subsidiaries or branches. One
 * team and one set of settings; each form belongs to one organisation (its name and logo on the form's
 * public pages), and the rail's switcher narrows forms, responses and analytics to one of them.
 */
export interface Organisation {
  id: string
  name: string
  /** A short name for tight places (rail, badges), e.g. "RL UK". */
  short_name: string | null
  logo_url: string | null
  website: string | null
  /** The workspace's first organisation: can't be archived, takes forms without one. */
  main: boolean
  status: 'active' | 'archived'
  forms_count: number
  responses_count: number
  created_at: string
  updated_at: string
}

/** POST / PATCH /organisations: an upload id replaces the logo, null removes it, left out keeps it. */
export interface OrganisationSaveRequest {
  name: string
  short_name: string | null
  website: string | null
  logo_upload_id?: string | null
}

/** The request header that narrows lists to one organisation (absent = all). */
export const ORGANISATION_HEADER = 'x-formalie-organisation'
