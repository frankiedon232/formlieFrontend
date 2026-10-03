/**
 * The system template catalogue (F9): every definition, a summary for the gallery and the full
 * form (schema + design) for "Use template". Shared by the app and the API mock.
 */
import { allFields, type FormField } from '../utils/forms/build'
import { isInputField } from '../utils/forms/fields'
import type { FormSchemaV1 } from '../utils/forms/schema'
import { applyPatch, defaultTheme, type FormTheme, type WorkspaceBranding } from '../utils/forms/theme'
import { BUSINESS_TEMPLATES } from './catalogue/business'
import { EDUCATION_TEMPLATES } from './catalogue/education'
import { EVENTS_TEMPLATES } from './catalogue/events'
import { FINANCE_LEGAL_TEMPLATES } from './catalogue/finance-legal'
import { HEALTH_SAFETY_TEMPLATES } from './catalogue/health-safety'
import { HOSPITALITY_TEMPLATES } from './catalogue/hospitality'
import { HR_TEMPLATES } from './catalogue/hr'
import { OPERATIONS_IT_TEMPLATES } from './catalogue/operations-it'
import { TEMPLATE_CATEGORIES, categoryOf, type TemplateCategoryKey } from './categories'
import { buildSchema, type TemplateDef } from './kit'

export { TEMPLATE_CATEGORIES, TEMPLATE_CATEGORY_KEYS, categoryOf } from './categories'
export type { TemplateCategoryKey } from './categories'
export type { TemplateDef } from './kit'

export const SYSTEM_TEMPLATES: TemplateDef[] = [
  ...BUSINESS_TEMPLATES,
  ...HR_TEMPLATES,
  ...HEALTH_SAFETY_TEMPLATES,
  ...EVENTS_TEMPLATES,
  ...HOSPITALITY_TEMPLATES,
  ...EDUCATION_TEMPLATES,
  ...OPERATIONS_IT_TEMPLATES,
  ...FINANCE_LEGAL_TEMPLATES,
]

const byKey = new Map(SYSTEM_TEMPLATES.map(def => [def.key, def]))
export const systemTemplate = (key: string) => byKey.get(key)

/** Category design, then the template's own accents (logo follows the workspace). */
export function templateTheme(def: TemplateDef, branding?: WorkspaceBranding): FormTheme {
  const base = defaultTheme(branding)
  const category = categoryOf(def.category)
  return applyPatch(applyPatch(base, category?.design ?? {}), def.design ?? {})
}

/** The form a template creates: schema with its design (theme) in it. */
export function templateSchema(def: TemplateDef, branding?: WorkspaceBranding): FormSchemaV1 {
  return { ...buildSchema(def), theme: templateTheme(def, branding) as unknown as Record<string, unknown> }
}

export interface TemplateStats {
  pages: number
  fields: number
  logic: number
  calculations: number
}

export function schemaStats(schema: FormSchemaV1): TemplateStats {
  const fields = allFields(schema)
  return {
    pages: schema.pages.length,
    fields: fields.filter(f => isInputField(f.type) && f.type !== 'calculated' && f.type !== 'hidden').length,
    logic: schema.logic?.length ?? 0,
    calculations: fields.filter(f => f.type === 'calculated').length,
  }
}

/** First questions, for the gallery thumbnail. */
export const previewLabels = (schema: FormSchemaV1, count = 3) =>
  allFields(schema)
    .filter((f: FormField) => isInputField(f.type) && f.type !== 'hidden' && f.type !== 'calculated')
    .slice(0, count)
    .map(f => f.label)

export const categoryCounts = () =>
  Object.fromEntries(TEMPLATE_CATEGORIES.map(c => [c.key, SYSTEM_TEMPLATES.filter(t => t.category === c.key).length])) as Record<
    TemplateCategoryKey,
    number
  >
