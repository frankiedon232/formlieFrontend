/** Form list shapes (docs/API-CONTRACT.md → Forms). */
export type FormStatus = 'draft' | 'published' | 'closed' | 'archived'

export interface FormOwner {
  id: string
  name: string
}

export interface FormFolder {
  id: string
  name: string
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
}
