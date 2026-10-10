/** Templates gallery (F9), docs/API-CONTRACT.md → Templates. */
import type { FormSchemaV1 } from '../utils/forms/schema'

export type TemplateSource = 'system' | 'workspace'

export interface TemplateSummary {
  /** System: catalogue key (`risk_assessment`); workspace: `ws_<id>`. */
  key: string
  source: TemplateSource
  category: string
  icon: string
  /** In the requested language for system templates; as written for workspace templates. */
  name: string
  description: string
  tags: string[]
  minutes: number
  pages_count: number
  fields_count: number
  logic_count: number
  calculations_count: number
  /** Full design tokens, the gallery card shows a mini preview in this design. */
  theme: Record<string, unknown>
  /** First question labels, for the card preview. */
  preview: string[]
  /** Forms created from this template (not in Trash), their responses and the last use. */
  forms_count: number
  responses_count: number
  last_used_at: string | null
  created_by: { id: string; name: string } | null
  updated_at: string
  /** Workspace templates: the form it was saved from (null for copies and system templates). */
  source_form_id: string | null
  /** What the signed-in person may do with it (F22 R2 M3: own · all; Formalie's own items are use-only). */
  can?: { edit: boolean; delete: boolean }
}

export interface TemplateCalculation {
  label: string
  formula: string
  /** Worked out for the team, not shown to respondents. */
  internal: boolean
}

export interface TemplateDetail extends TemplateSummary {
  schema: FormSchemaV1
  calculations: TemplateCalculation[]
}

/**
 * GET /templates/insights?from=&to=, the two top cards of the template pages (locked list format,
 * owner 2026-10-04): forms made from templates in the period (and the one before), per day, all
 * time, how many templates there are, and use per category (most used first).
 */
export interface TemplateInsights {
  period: { from: string; to: string; count: number; previous: number }
  daily: { date: string; count: number }[]
  /** Forms made from any template, not in Trash. */
  forms_total: number
  system_count: number
  workspace_count: number
  categories: { key: string; forms: number }[]
}

/** GET /templates/facets, counts for the category filter (system + workspace). */
export interface TemplateFacets {
  total: number
  categories: Record<string, number>
  workspace: number
}

/** GET /templates/categories, Formalie's categories with what's inside (owner, 2026-10-03). */
export interface TemplateCategorySummary {
  key: string
  /** In the requested language. */
  name: string
  icon: string
  templates_count: number
  /** Templates with calculations / with logic. */
  calculations_count: number
  logic_count: number
  /** Forms made from this category's templates, their responses and the last use. */
  forms_count: number
  responses_count: number
  last_used_at: string | null
  /** The category's design (full tokens) for the card preview. */
  theme: Record<string, unknown>
  /** A few template names in the category, most used first. */
  examples: string[]
}
