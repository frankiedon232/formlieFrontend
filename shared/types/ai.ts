import type { FormField } from '../utils/forms/build'
import type { FormSchemaV1 } from '../utils/forms/schema'

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
  /** The workspace's brand colour (read only here), where designs start from. */
  brand_color?: string | null
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
  /** For requests made in the app: what it did, translated in the app (the `result` text is the fallback). */
  notes?: AiNote[]
  stats?: AiDraftStats
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

/** One thing the assistant did, translated in the app (`ai.note.<code>`). */
export interface AiNote {
  /** A theme's key (translated in the app: ai.theme.<key>), passed to the text as {theme}. */
  theme?: AiTheme
  code: 'follow_up' | 'total' | 'pages' | 'document_questions' | 'document_sections' | 'document_none' | 'added_contact' | 'from_list' | 'template' | 'try_again' | 'basic' | 'themes' | 'low_rating' | 'other_option' | 'from_template' | 'common' | 'consent' | 'assist_found' | 'assist_applied' | 'busiest_day' | 'responses_up' | 'responses_down' | 'rating_up' | 'rating_down' | 'theme_negative' | 'theme_positive' | 'no_text' | 'few_responses' | 'period_default' | 'field_guess' | 'no_field' | 'no_answers'
  params?: Record<string, string | number>
}

/** What a draft is made of, for the badges next to the preview. */
export interface AiDraftStats {
  pages: number
  fields: number
  logic: number
  calculations: number
}

/** POST /ai/forms/draft: a form to preview, then create (or try again / discard). */
export interface AiFormDraft {
  request_id: string
  name: string
  description: string
  schema: FormSchemaV1
  /** What the assistant did. */
  notes: AiNote[]
  /** The Formalie template it started from, if any. */
  based_on: { key: string; name: string } | null
  source: 'document' | 'list' | 'template' | 'basic'
  stats: AiDraftStats
  credits: number
}

/** POST /ai/templates/draft: a template idea with a matching design. */
export interface AiTemplateDraft extends AiFormDraft {
  category: string
}

export interface AiThemeSuggestion {
  key: string
  name: string
  description: string
  tokens: Record<string, unknown>
}

/** POST /ai/themes/draft: three designs from a brand colour, previewed on a sample form. */
export interface AiThemeDraft {
  request_id: string
  colour: string
  suggestions: AiThemeSuggestion[]
  sample: FormSchemaV1
  credits: number
}

/** POST /ai/requests/{id}/apply: what was made. */
export interface AiApplyResult {
  target: AiTarget
}

/** In the builder (F19 M3): what the assistant is asked to do with the form being edited. */
export const AI_ASSIST_ACTIONS = ['fields', 'help', 'logic', 'check'] as const
export type AiAssistAction = (typeof AI_ASSIST_ACTIONS)[number]

/** Problems "Check my form" looks for (translated in the app: ai.problem.<code>). */
export type AiProblem = 'email_type' | 'phone_type' | 'date_type' | 'number_type' | 'duplicate' | 'image_alt' | 'long_label' | 'no_required' | 'few_options' | 'long_page' | 'no_label'

/** One proposed change; the builder applies it (one undo step each) or skips it. */
export type AiSuggestion =
  | { id: string; kind: 'add_field'; field: FormField; page_id: string; after_id: string | null; note: AiNote }
  | { id: string; kind: 'set_help'; field_id: string; label: string; help: string }
  | { id: string; kind: 'add_rule'; rule: Record<string, unknown>; note: AiNote }
  | { id: string; kind: 'fix'; field_id: string | null; label: string; problem: AiProblem; patch: Partial<FormField> | null; remove?: boolean }

/** POST /ai/forms/{id}/assist */
export interface AiAssistResult {
  request_id: string
  action: AiAssistAction
  suggestions: AiSuggestion[]
  credits: number
}

/** Themes the assistant finds in written answers (translated in the app: ai.theme.<key>). */
export const AI_THEMES = ['speed', 'ease', 'staff', 'price', 'quality', 'mobile', 'communication', 'scheduling', 'location', 'delivery', 'other'] as const
export type AiTheme = (typeof AI_THEMES)[number]

export interface AiSentiment {
  positive: number
  neutral: number
  negative: number
}

/** POST /ai/analysis (and /ai/digest): what a form's responses say over a period, against the period before. */
export interface AiAnalysis {
  request_id: string
  form: { id: string; name: string }
  period: { from: string; to: string }
  previous: { from: string; to: string }
  totals: { responses: number; previous: number; text_answers: number }
  daily: { date: string; count: number }[]
  sentiment: AiSentiment
  previous_sentiment: AiSentiment
  themes: { key: AiTheme; count: number; share: number; positive: number; negative: number; examples: string[] }[]
  ratings: { key: string; label: string; average: number; previous: number | null; max: number }[]
  choices: { key: string; label: string; top: string; share: number }[]
  findings: AiNote[]
  credits: number
}

/** POST /ai/ask: a question in plain words about one form's responses, with the numbers and the filters used. */
export interface AiAnswer {
  request_id: string
  question: string
  kind: 'count' | 'top' | 'average' | 'trend'
  value: number | null
  field: { key: string; label: string } | null
  rows: { label: string; count: number; share: number }[]
  filters: { kind: 'period' | 'status' | 'answer'; label: string; value: string }[]
  period: { from: string; to: string } | null
  notes: AiNote[]
  credits: number
}

/** POST /ai/responses/{id}/summary: one response in a few lines. */
export interface AiResponseSummary {
  request_id: string
  points: { label: string; value: string }[]
  sentiment: keyof AiSentiment | null
  themes: AiTheme[]
  credits: number
}
