/**
 * Responses (F11, docs/API-CONTRACT.md → Responses). One shape for the per-form list, the inbox
 * across forms and the detail panel; insights summarise a form's (or the workspace's) responses.
 */
import type { FormSchemaV1 } from '../utils/forms/schema'

/** Review status: new until someone looks at it; reviewed, approved or rejected after. */
export type ResponseStatus = 'new' | 'reviewed' | 'approved' | 'rejected'
export const RESPONSE_STATUSES: ResponseStatus[] = ['new', 'reviewed', 'approved', 'rejected']

export interface ResponseRespondent {
  name: string | null
  email: string | null
  /** How we know: an invitation, a signed-in member, or what they typed in the form ('anonymous' = the form asks no name or email). */
  kind: 'invite' | 'member' | 'answer' | 'anonymous'
  /**
   * What names this response, only from what the form collected (owner 2026-10-09: no data outside the
   * form): the name, else the email, else its first answers ("Country 2 · State 2-1"); null when nothing was answered.
   */
  title?: string | null
}

export interface ResponseRow {
  id: string
  /** Running number within the form (#1 = the first response). */
  number: number
  form: { id: string; name: string }
  submitted_at: string
  status: ResponseStatus
  tags: string[]
  respondent: ResponseRespondent
  channel: 'link' | 'embed' | 'api'
  language: string
  /** Time spent filling in (null when unknown). */
  duration_seconds: number | null
  /** Answers by field key (per-form lists; the inbox sends none). */
  answers: Record<string, unknown>
  notes_count: number
  /** How complete it is: questions answered of the questions the form asks (cards' progress bar). */
  answered: number
  questions: number
  /** Files attached across the answers. */
  files_count: number
  edited: boolean
  /** Flagged as perhaps the same person as an earlier response (F10 identity). */
  possible_duplicate: { of: string; reason: string } | null
}

export interface ResponseNote {
  id: string
  author: { id: string; name: string }
  text: string
  created_at: string
}

/** One change to a response (status, tags, an edited answer), newest first. */
export interface ResponseChange {
  id: string
  at: string
  by: { id: string; name: string }
  field: string
  before: unknown
  after: unknown
}

export interface ResponseDetail extends ResponseRow {
  /** Every answer by field key. */
  data: Record<string, unknown>
  form_version: number | null
  /** The version the respondent filled in (questions in its order). */
  schema: FormSchemaV1
  meta: { device: string; country: string | null }
  notes: ResponseNote[]
  history: ResponseChange[]
  /** What the person may do: review (status, tags, notes) and edit answers / delete. */
  /** Review = status, tags, notes; edit = correct answers; delete. Role and form access together. */
  can: { review: boolean; edit: boolean; delete: boolean }
}

export type QuestionInsight =
  | { key: string; label: string; type: string; answered: number; kind: 'choice'; multiple: boolean; options: { value: string; label: string; count: number }[] }
  | { key: string; label: string; type: string; answered: number; kind: 'rating'; average: number; min: number; max: number; distribution: { value: number; count: number }[] }
  | { key: string; label: string; type: string; answered: number; kind: 'number'; average: number; min: number; max: number; median: number }
  | { key: string; label: string; type: string; answered: number; kind: 'text'; latest: { id: string; value: string; at: string }[] }
  | { key: string; label: string; type: string; answered: number; kind: 'other' }

export interface ResponseInsights {
  total: number
  /** Not yet reviewed. */
  new: number
  /** The chosen period and the same length before it (trend). */
  period: { from: string; to: string; count: number; previous: number }
  /** One entry per day in the period. */
  daily: { date: string; count: number }[]
  status: Record<ResponseStatus, number>
  channels: { link: number; embed: number; api: number }
  languages: { code: string; count: number }[]
  /** Median time to fill in, in seconds (null when unknown). */
  median_seconds: number | null
  /** Share of started fill-ins that were sent (0–100; per form only). */
  completion_rate: number | null
  last_at: string | null
  /** Per question (per form only, empty in the inbox). */
  questions: QuestionInsight[]
  /** Inbox only: the busiest forms in the period. */
  top_forms: { id: string; name: string; count: number }[]
  /** Per form: the questions (what respondents fill in), for table columns and the summary. */
  schema: FormSchemaV1 | null
}

/** One form in the Responses page, grouped by form (owner 2026-10-04): its responses at a glance. */
export interface ResponseFormRow {
  id: string
  name: string
  status: 'draft' | 'published' | 'closed' | 'archived'
  folder: { id: string; name: string } | null
  owner: { id: string; name: string }
  public_key: string
  custom_link: string | null
  completion_rate: number
  total: number
  /** By review status. */
  status_counts: Record<ResponseStatus, number>
  last_at: string | null
  /** Responses per day, the last 30 days (sparkline). */
  daily: number[]
  /** Where its responses are kept (F12 M2). */
  storage?: import('./destinations').StorageMark
}


/**
 * Response exports (F11 M3): a file of a form's responses, made in the background with progress.
 * `scope`: all responses, the ones matching the list's filters, or the selected ones. The file is
 * kept 7 days (`expires_at`); each download asks for a one-time private link.
 */
export type ResponseExportFormat = 'xlsx' | 'csv' | 'pdf'
export type ResponseExportScope = 'all' | 'filtered' | 'selected'
export interface ResponseExport {
  id: string
  form: { id: string; name: string }
  format: ResponseExportFormat
  scope: ResponseExportScope
  status: 'queued' | 'running' | 'ready' | 'expired' | 'failed'
  /** 0–100 */
  progress: number
  rows: number
  columns: number
  file_name: string
  size: number | null
  created_by: { id: string; name: string }
  created_at: string
  expires_at: string
}
