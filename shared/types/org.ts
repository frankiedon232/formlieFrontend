/**
 * Organisation data (F14 M2, docs/API-CONTRACT.md → Organisation data): each workspace's own departments,
 * job titles (teams and locations were dropped, owner 2026-10-07: forms are not team work; people get access per form). The form builder, field access and logic only ever
 * offer what the workspace has here. Job titles are what people do, not permission roles (F22).
 */
export const ORG_KINDS = ['departments', 'job_titles'] as const
export type OrgKind = (typeof ORG_KINDS)[number]
export type OrgStatus = 'active' | 'archived'

export interface OrgPerson {
  id: string
  name: string
  email: string
}

export interface OrgItem {
  id: string
  kind: OrgKind
  name: string
  /** A short code people use (e.g. FIN, HR-02, a cost centre number). */
  code: string | null
  description: string | null
  status: OrgStatus
  /** The people in it (a person may be in several). */
  members: OrgPerson[]
  /** Forms with a field restricted to it (field access). */
  forms_count: number
  created_at: string
  updated_at: string
  archived_at: string | null
}

/** One form using an entry, and the fields that are restricted to it. */
export interface OrgUsage {
  form: { id: string; name: string; status: string }
  fields: string[]
}

export interface OrgItemSaveRequest {
  name: string
  code: string | null
  description: string | null
  member_ids: string[]
}

export interface OrgInsights {
  total: number
  by_status: Record<OrgStatus, number>
  /** People in the workspace, and how many belong to at least one active entry of this kind. */
  people: number
  people_assigned: number
  /** Active entries with nobody in them. */
  empty: number
  /** The biggest active entries by people, for the bars. */
  largest: { id: string; name: string; count: number }[]
}

export interface OrgImportResult {
  created: number
  skipped: { name: string; reason: 'duplicate' | 'too_long' | 'empty' }[]
}
