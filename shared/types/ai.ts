/**
 * AI assistant (F19, docs/API-CONTRACT.md → AI assistant). The assistant proposes, a person applies:
 * every request is kept (who, what, when, the result and whether it was applied) for the workspace's
 * chosen number of days, counted against the monthly allowance and recorded in the audit trail.
 */

/** What a request was for; each kind costs a number of credits (`AI_CREDITS`). */
export const AI_KINDS = ['form', 'template', 'theme', 'builder', 'analysis', 'question', 'summary', 'translate', 'rewrite'] as const
export type AiKind = (typeof AI_KINDS)[number]

/** Proposed = waiting for a person; applied or discarded by them; failed = nothing came back. */
export const AI_STATUSES = ['proposed', 'applied', 'discarded', 'failed'] as const
export type AiStatus = (typeof AI_STATUSES)[number]

/** What the assistant may read in this workspace. */
export const AI_SOURCES = ['forms', 'responses', 'data'] as const
export type AiSource = (typeof AI_SOURCES)[number]

/** How long requests (the prompt and the result) are kept. */
export const AI_KEEP_DAYS = [30, 90, 180, 365] as const

export interface AiSettings {
  enabled: boolean
  sources: Record<AiSource, boolean>
  /** Names, emails, phone numbers and similar are replaced before anything is sent to the model. */
  mask_personal: boolean
  keep_days: (typeof AI_KEEP_DAYS)[number]
  /** The monthly allowance of credits (from the plan, F24). */
  monthly_credits: number
  updated_at: string | null
  updated_by: { id: string; name: string } | null
}

export interface AiUsage {
  /** First and last day of this month's period (ISO dates). */
  period: { start: string; end: string }
  used: number
  limit: number
  /** Credits used in the same number of days of the month before. */
  previous: number
  requests: number
  people: number
  daily: { date: string; count: number }[]
  by_kind: Record<AiKind, number>
}

export interface AiTarget {
  type: 'form' | 'template' | 'theme' | 'response'
  id: string
  name: string
}

export interface AiRequestRow {
  id: string
  kind: AiKind
  status: AiStatus
  /** A short title for the request ("Visitor sign-in form"). */
  title: string
  by: { id: string; name: string }
  /** What it was about or what it made (opens it), if anything. */
  target: AiTarget | null
  credits: number
  created_at: string
  applied_at: string | null
  /** The signed-in person made it (they may delete it). */
  mine: boolean
}

export interface AiRequestDetail extends AiRequestRow {
  /** What the person asked, with personal data masked when the workspace asks for it. */
  prompt: string
  /** A plain-language summary of what came back. */
  result: string
  /** Which parts of the workspace it read. */
  read: AiSource[]
  masked: boolean
  /** When the request will be removed (the workspace's keep setting). */
  expires_at: string
}

export interface AiRequestInsights {
  total: number
  previous: number
  daily: { date: string; count: number }[]
  by_status: Record<AiStatus, number>
  by_kind: Record<AiKind, number>
  people: number
  credits: number
}
