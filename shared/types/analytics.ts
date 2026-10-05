/**
 * Form analytics (F18, docs/API-CONTRACT.md → Analytics): how people move through forms. A view is
 * the form opened, a start is the first answer, a completion is a submitted response. Counts are
 * per period; nothing here names a respondent.
 */
import type { FormStatus } from './forms'

export interface AnalyticsTotals {
  views: number
  starts: number
  completions: number
  /** Completions of starts, 0 to 100. */
  completion_rate: number
  /** Median time to fill in, seconds (null without completions). */
  median_seconds: number | null
}

export interface AnalyticsDay {
  date: string
  views: number
  starts: number
  completions: number
}

/** GET /analytics/overview?from&to (the workspace, or one form with `form`). */
export interface AnalyticsOverview {
  from: string
  to: string
  totals: AnalyticsTotals
  /** The same length of time just before `from`. */
  previous: AnalyticsTotals
  daily: AnalyticsDay[]
  /** How people came in (completions). */
  channels: Record<'link' | 'embed' | 'api', number>
  /** Forms with at least one view in the period. */
  active_forms: number
}

/** Where most people stop in a form. */
export interface DropOffPoint {
  page: number
  page_title: string | null
  field: string | null
  field_label: string | null
  /** Share of starters who left there, 0 to 100. */
  rate: number
}

/** GET /analytics/forms (DataView: q, sort, page). */
export interface FormAnalyticsRow extends AnalyticsTotals {
  id: string
  name: string
  status: FormStatus
  /** Completions change against the period before, percent (null: nothing before). */
  change: number | null
  /** Completions per day in the period (sparkline). */
  trend: number[]
  drop_off: DropOffPoint | null
}

export interface FunnelPage {
  index: number
  title: string | null
  /** Starters who reached the page. */
  reached: number
  /** Of those, how many left on it. */
  left: number
}

export interface FunnelField {
  key: string
  label: string
  type: string
  page: number
  required: boolean
  /** Starters who saw the question. */
  reached: number
  answered: number
  /** Left the form on this question. */
  left: number
  /** Median seconds spent on it. */
  seconds: number
}

/** GET /analytics/forms/{id}/funnel?from&to. */
export interface FormFunnel {
  form: { id: string; name: string; status: FormStatus }
  totals: AnalyticsTotals
  pages: FunnelPage[]
  fields: FunnelField[]
}
