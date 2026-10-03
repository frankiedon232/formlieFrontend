/** Templates gallery (F9) — docs/API-CONTRACT.md → Templates. */
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
  /** Full design tokens — the gallery card shows a mini preview in this design. */
  theme: Record<string, unknown>
  /** First question labels, for the card preview. */
  preview: string[]
  /** Forms created from this template (not in Trash), their responses and the last use. */
  forms_count: number
  responses_count: number
  last_used_at: string | null
  created_by: { id: string; name: string } | null
  updated_at: string
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

/** GET /templates/facets — counts for the category filter (system + workspace). */
export interface TemplateFacets {
  total: number
  categories: Record<string, number>
  workspace: number
}
