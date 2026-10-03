/**
 * Template authoring kit (F9). A template is written as a short definition and built into a real
 * form schema — the same shape the builder saves — plus its design (theme tokens). Every template
 * is checked in tests: valid schema, publishable, formulas valid, logic targets exist.
 *
 *   const t: TemplateDef = {
 *     key: 'risk_assessment', category: 'health_safety', icon: 'i-lucide-shield-alert', minutes: 8,
 *     name: 'Risk Assessment', description: '…', design: { … },
 *     pages: [page('Hazard', [
 *       row(q('short_text', 'Hazard', { key: 'hazard', required: true })),
 *       row(q('radio', 'Likelihood', { key: 'likelihood', options: scored(['Rare', 1], ['Likely', 4]) }), …),
 *       q('calculated', 'Risk score', { key: 'risk_score', formula: '{likelihood} * {severity}' }),
 *     ])],
 *     logic: [rule([['risk_score', 'gte', 15]], [['show', 'action_plan']])],
 *   }
 *
 * Content is English here; names / descriptions / categories are translated in i18n
 * (`templates.items.<key>`), the questions themselves in milestone 5 (per-template message files).
 */
import type { FormField } from '../utils/forms/build'
import type { FieldType } from '../utils/forms/fields'
import { hasOptions } from '../utils/forms/fields'
import type { LogicAction, LogicCondition, LogicOperator, LogicRule, LogicValue } from '../utils/forms/logic'
import { END_OF_FORM } from '../utils/forms/logic'
import type { FormSchemaV1 } from '../utils/forms/schema'
import type { ThemePatch } from '../utils/forms/theme'
import type { TemplateCategoryKey } from './categories'

export interface FieldOptions {
  /** Stable key (formulas and logic refer to it). Defaults to one made from the label. */
  key?: string
  required?: boolean
  help?: string
  placeholder?: string
  /** 1–12 columns; fields given to `row()` share the row equally unless set. */
  width?: number
  readonly?: boolean
  options?: { value: string; label: string; score?: number }[]
  validation?: Record<string, unknown>
  props?: Record<string, unknown>
  /** Calculated fields. */
  formula?: string
  default?: unknown
}

export interface FieldSeed extends FieldOptions {
  type: FieldType
  label: string
}

export interface RowSeed {
  fields: FieldSeed[]
}

export interface PageSeed {
  title: string
  rows: RowSeed[]
}

export interface RuleSeed {
  match: 'all' | 'any'
  when: { key: string; op: LogicOperator; value?: LogicValue }[]
  then: { action: LogicAction; target?: string; value?: LogicValue }[]
}

export interface TemplateDef {
  key: string
  category: TemplateCategoryKey
  icon: string
  /** Typical time to fill in, in minutes. */
  minutes: number
  /** English name / description (translations: i18n `templates.items.<key>`). */
  name: string
  description: string
  tags?: string[]
  /** Design on top of the category's design. */
  design?: ThemePatch
  pages: PageSeed[]
  logic?: RuleSeed[]
  thankYou?: { title: string; message: string }
}

// ── Authoring helpers ────────────────────────────────────────────────────────────────

/** One question / block. */
export const q = (type: FieldType, label: string, options: FieldOptions = {}): FieldSeed => ({ type, label, ...options })

/** Fields side by side (they share the 12 columns). A bare field is a row of its own. */
export const row = (...fields: FieldSeed[]): RowSeed => ({ fields })

export const page = (title: string, items: (RowSeed | FieldSeed)[]): PageSeed => ({
  title,
  rows: items.map(item => ('fields' in item ? item : row(item))),
})

/** Plain options: `opts('Yes', 'No')`. */
export const opts = (...labels: string[]) => labels.map(label => ({ value: slug(label), label }))

/** Options that carry a number for calculations: `scored(['Rare', 1], ['Likely', 4])`. */
export const scored = (...pairs: [string, number][]) => pairs.map(([label, score]) => ({ value: slug(label), label, score }))

/** Agree / disagree answers scored 1–5 (surveys, averages). */
export const agreeScale = () =>
  scored(['Strongly disagree', 1], ['Disagree', 2], ['Neutral', 3], ['Agree', 4], ['Strongly agree', 5])

/**
 * Logic: `rule([['risk_score', 'gte', 15]], [['show', 'action_plan']])` — targets are field keys,
 * page titles or END_OF_FORM; `match: 'any'` for "any condition".
 */
export const rule = (
  conditions: [string, LogicOperator, LogicValue?][],
  effects: [LogicAction, string?, LogicValue?][],
  match: 'all' | 'any' = 'all',
): RuleSeed => ({
  match,
  when: conditions.map(([key, op, value]) => ({ key, op, value })),
  then: effects.map(([action, target, value]) => ({ action, target, value })),
})

// ── Building ─────────────────────────────────────────────────────────────────────────

export const slug = (text: string) =>
  text
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 48) || 'field'

/** A key that starts with a letter and is unique in the form. */
function uniqueKey(wanted: string, taken: Set<string>) {
  let base = slug(wanted)
  if (!/^[a-z]/.test(base)) base = `q_${base}`
  let key = base
  for (let n = 2; taken.has(key); n++) key = `${base}_${n}`
  taken.add(key)
  return key
}

/**
 * The form schema for a template. Ids are stable (`f_<key>`, `p1`, `r1_2`, `rule1`) so logic and
 * calculations line up; a new form copies them as they are.
 */
export function buildSchema(def: TemplateDef): FormSchemaV1 {
  const taken = new Set<string>()
  const idOf = new Map<string, string>()
  let rowCount = 0
  const pages = def.pages.map((pageSeed, p) => ({
    id: `p${p + 1}`,
    title: pageSeed.title,
    rows: pageSeed.rows.map(rowSeed => {
      rowCount += 1
      const share = Math.max(1, Math.floor(12 / rowSeed.fields.length))
      return {
        id: `r${rowCount}`,
        fields: rowSeed.fields.map(seed => {
          const key = uniqueKey(seed.key ?? seed.label, taken)
          const id = `f_${key}`
          idOf.set(key, id)
          return toField(seed, id, key, seed.width ?? share)
        }),
      }
    }),
  }))

  const pageIds = new Map(def.pages.map((pageSeed, p) => [slug(pageSeed.title), `p${p + 1}`]))
  const target = (name?: string) => (name === undefined ? undefined : name === END_OF_FORM ? END_OF_FORM : (idOf.get(name) ?? pageIds.get(slug(name)) ?? name))
  const logic: LogicRule[] = (def.logic ?? []).map((rule, index) => {
    const conditions: LogicCondition[] = rule.when.map(c => ({ field: idOf.get(c.key) ?? c.key, op: c.op, value: c.value ?? null }))
    return {
      id: `rule${index + 1}`,
      when: rule.match === 'any' ? { any: conditions } : { all: conditions },
      then: rule.then.map(effect => ({ action: effect.action, target: target(effect.target), ...(effect.value !== undefined ? { value: effect.value } : {}) })),
    }
  })

  return {
    schema_version: 1,
    settings: { progress_bar: pages.length > 1, save_resume: pages.length > 2, language: 'en' },
    pages,
    logic: logic as FormSchemaV1['logic'],
    calculations: [],
    thank_you: {
      title: def.thankYou?.title ?? 'Thank you!',
      message: def.thankYou?.message ?? 'Your response has been recorded.',
      redirect_url: null,
    },
  }
}

/** Same starting props as a field added in the builder (app/utils/forms/field-registry.ts). */
const DEFAULT_PROPS: Partial<Record<FieldType, Record<string, unknown>>> = {
  long_text: { rows: 4 },
  currency: { currency: 'USD' },
  full_name: { show_title: false, show_middle: false },
  consent: { text: '', link_label: '', link_href: '' },
  ip_address: { ip_version: 'any' },
  rating: { max: 5 },
  scale: { min: 0, max: 10, min_label: '', max_label: '' },
  slider: { min: 0, max: 100, step: 1 },
  file_upload: { max_files: 1, max_mb: 10, accept: '' },
  image_upload: { max_files: 1, max_mb: 10, accept: 'image/*' },
  address: { require_postal_code: true, require_region: false },
  matrix: { rows: ['Quality', 'Speed', 'Value'] },
  section: { description: '', size: 'lg', divider: true, align: 'start' },
  paragraph: { html: '' },
  divider: { style: 'solid', spacing: 'md' },
  hidden: { param: '' },
}

function toField(seed: FieldSeed, id: string, key: string, width: number): FormField {
  const props = { ...DEFAULT_PROPS[seed.type], ...seed.props, ...(seed.formula ? { formula: seed.formula } : {}) }
  return {
    id,
    key,
    type: seed.type,
    label: seed.label,
    width: Math.min(12, Math.max(1, width)),
    required: !!seed.required,
    ...(seed.help ? { help: seed.help } : {}),
    ...(seed.placeholder ? { placeholder: seed.placeholder } : {}),
    ...(seed.readonly ? { readonly: true } : {}),
    ...(seed.validation ? { validation: seed.validation } : {}),
    ...(seed.default !== undefined ? { default: seed.default } : {}),
    ...(Object.keys(props).length ? { props } : {}),
    ...(seed.type === 'percentage' && !seed.validation ? { validation: { min: 0, max: 100 } } : {}),
    ...(hasOptions(seed.type) ? { options: seed.options ?? opts('Option 1', 'Option 2', 'Option 3') } : {}),
  } as FormField
}
