/** Form list shapes (docs/API-CONTRACT.md → Forms). */
export type FormStatus = 'draft' | 'published' | 'closed' | 'archived'

export interface FormOwner {
  id: string
  name: string
}

export interface FormFolder {
  id: string
  name: string
  /** Forms in the folder (not counting trash). */
  forms_count?: number
}

export interface FormSummary {
  id: string
  name: string
  slug: string
  status: FormStatus
  has_unpublished_changes: boolean
  folder: FormFolder | null
  owner: FormOwner
  tags: string[]
  responses_count: number
  /** 0–100: share of started sessions that were submitted. */
  completion_rate: number
  created_at: string
  updated_at: string
  /** Optimistic locking: send it back on every change; a mismatch → FRM-GEN-1009. */
  row_version: number
  /** Set while the form is in Trash (kept 30 days, then removed for good). */
  deleted_at: string | null
}

/** GET /forms/facets — options for the owner and tag filters. */
export interface FormFacets {
  owners: FormOwner[]
  tags: string[]
}

export type FormLifecycleAction = 'unpublish' | 'close' | 'reopen' | 'archive' | 'unarchive' | 'restore'

export type FormBulkAction = 'archive' | 'move' | 'delete' | 'restore' | 'purge'

/** POST /forms/bulk → what happened to each selected form. */
export interface FormBulkResult {
  updated: number
  failed: { id: string; code: string }[]
}

export const TRASH_RETENTION_DAYS = 30

/** GET /forms/:id/versions item — a published snapshot (the schema comes from GET …/versions/:vid). */
export interface FormVersion {
  id: string
  number: number
  published_at: string
  published_by: { id: string; name: string }
  change_summary: string | null
  fields_count: number
}
