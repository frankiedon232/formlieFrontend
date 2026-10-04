import { allFields, cannotBeRequired, newId, type FormField } from '#shared/utils/forms/build'
import { isInputField } from '#shared/utils/forms/fields'
import { formulaKeys, isValidFormula } from '#shared/utils/forms/formula'
import {
  actionTarget,
  needsValue,
  operatorsFor,
  takesCount,
  takesRange,
  type LogicAction,
  type LogicCondition,
  type LogicEffect,
  type LogicRule,
  type LogicValue,
} from '#shared/utils/forms/logic'

/**
 * The logic editor's model on top of the builder schema: rule CRUD (every change is one undo
 * step), the plain-language summary ("When Severity is High, require Photos."), starter rules,
 * and checks that catch mistakes before respondents hit them (deleted fields, a required field
 * nobody can fill in, a rule that hides the field it depends on …).
 */
export function useLogicRules() {
  const { t } = useI18n()
  const builder = useBuilder()

  const rules = computed<LogicRule[]>(() => (builder.schema.value?.logic ?? []) as LogicRule[])
  const fields = computed(() => (builder.schema.value ? allFields(builder.schema.value) : []))
  /** Fields a condition can test: everything that holds an answer (hidden and calculated too). */
  const sources = computed(() => fields.value.filter(f => isInputField(f.type)))
  const pages = computed(() => builder.schema.value?.pages ?? [])
  const fieldById = computed(() => new Map(fields.value.map(f => [f.id, f])))
  const label = (f: FormField | undefined) => f?.label?.trim() || (f ? t('builder.untitled') : t('logic.missing'))
  const pageLabel = (id: string) => {
    const i = pages.value.findIndex(p => p.id === id)
    return i < 0 ? t('logic.missing') : pages.value[i]!.title || t('builder.page.default', { n: i + 1 })
  }

  /** What an action may point at. */
  function targetsFor(action: LogicAction) {
    const kind = actionTarget(action)
    if (kind === 'page') return pages.value.map(p => ({ value: p.id, label: pageLabel(p.id), icon: 'i-lucide-file' }))
    if (kind === 'none') return []
    const list =
      kind === 'field'
        ? fields.value
        : fields.value.filter(
            f => isInputField(f.type) && f.type !== 'calculated' && (action !== 'require' || f.type !== 'hidden'),
          )
    return list.map(f => ({ value: f.id, label: label(f), icon: fieldIcon(f.type) }))
  }

  function mutate(change: (list: LogicRule[]) => void, group?: string) {
    if (!builder.schema.value) return
    builder.history.record(group)
    const list = structuredClone(toRaw(rules.value)) as LogicRule[]
    change(list)
    builder.schema.value.logic = list
  }

  function blankCondition(): LogicCondition {
    const first = sources.value[0]
    return { field: first?.id ?? '', op: first ? operatorsFor(first.type)[0]! : 'eq', value: null }
  }

  /** New rule; `preset` starts it with a common action so the user only fills in the blanks. */
  function addRule(preset: LogicAction = 'show'): string {
    const id = newId('rule')
    const target =
      actionTarget(preset) === 'page'
        ? (pages.value[1]?.id ?? '')
        : actionTarget(preset) === 'none'
          ? undefined
          : (fields.value.find(f => f.id !== sources.value[0]?.id)?.id ?? '')
    mutate(list => list.push({ id, when: { all: [blankCondition()] }, then: [{ action: preset, target }] }))
    return id
  }
  const update = (id: string, change: (rule: LogicRule) => void, group?: string) =>
    mutate(list => {
      const rule = list.find(r => r.id === id)
      if (rule) change(rule)
    }, group)
  const removeRule = (id: string) => mutate(list => list.splice(list.findIndex(r => r.id === id), 1))
  const duplicateRule = (id: string) =>
    mutate(list => {
      const i = list.findIndex(r => r.id === id)
      if (i >= 0) list.splice(i + 1, 0, { ...structuredClone(list[i]!), id: newId('rule') })
    })
  const moveRule = (id: string, delta: number) =>
    mutate(list => {
      const i = list.findIndex(r => r.id === id)
      const j = i + delta
      if (i < 0 || j < 0 || j >= list.length) return
      list.splice(j, 0, list.splice(i, 1)[0]!)
    })

  const conditionsOf = (rule: LogicRule) => rule.when.any ?? rule.when.all ?? []
  const matchOf = (rule: LogicRule): 'all' | 'any' => (rule.when.any ? 'any' : 'all')

  // ── Plain-language summary ─────────────────────────────────────────────────────────
  /** Human answer for a value (option labels, list, yes / no). */
  function valueText(field: FormField | undefined, value: LogicValue | undefined) {
    const one = (v: string | number) => field?.options?.find(o => o.value === String(v))?.label ?? String(v)
    if (Array.isArray(value)) return value.length ? value.map(one).join(t('logic.listJoin')) : '…'
    if (value === 'true') return t('logic.yes')
    if (value === 'false') return t('logic.no')
    return value == null || value === '' ? '…' : one(value)
  }
  function conditionText(c: LogicCondition) {
    const field = fieldById.value.get(c.field)
    return t(`logic.sentence.${c.op}`, {
      field: label(field),
      value: needsValue(c.op) ? (takesCount(c.op) ? String(c.value ?? '…') : valueText(field, c.value)) : '',
      value2: takesRange(c.op) ? valueText(field, c.value2 ?? null) : '',
    })
  }
  function actionText(a: LogicEffect) {
    const kind = actionTarget(a.action)
    const target = kind === 'page' ? pageLabel(a.target ?? '') : label(fieldById.value.get(a.target ?? ''))
    return t(`logic.sentence.${a.action}`, { target, value: valueText(fieldById.value.get(a.target ?? ''), a.value) })
  }
  function summary(rule: LogicRule) {
    const join = matchOf(rule) === 'any' ? t('logic.or') : t('logic.and')
    return t('logic.sentence.rule', {
      conditions: conditionsOf(rule).map(conditionText).join(join),
      actions: rule.then.map(actionText).join(t('logic.listJoin')),
    })
  }

  // ── Checks ─────────────────────────────────────────────────────────────────────────
  const emptyValue = (v: LogicValue | undefined) => v == null || v === '' || (Array.isArray(v) && !v.length)
  const pageOfField = (fieldId: string) =>
    pages.value.findIndex(p => p.rows.some(r => r.fields.some(f => f.id === fieldId)))

  /** Every problem with a rule (empty = fine). */
  function problems(rule: LogicRule): string[] {
    const found: string[] = []
    const conditions = conditionsOf(rule)
    for (const c of conditions) {
      if (!fieldById.value.has(c.field)) found.push(t('logic.problem.field'))
      else if (needsValue(c.op) && emptyValue(c.value) && !(takesRange(c.op) && !emptyValue(c.value2)))
        found.push(t('logic.problem.value'))
    }
    const tested = new Set(conditions.map(c => c.field))
    for (const a of rule.then) {
      const kind = actionTarget(a.action)
      const target = a.target ?? ''
      if (kind === 'page' && !pages.value.some(p => p.id === target)) found.push(t('logic.problem.target'))
      if (kind === 'field' || kind === 'input') {
        const field = fieldById.value.get(target)
        if (!field) found.push(t('logic.problem.target'))
        else {
          if (a.action === 'require' && cannotBeRequired(field))
            found.push(t('logic.problem.requireLocked'))
          if (['hide', 'disable', 'clear_value'].includes(a.action) && tested.has(target)) found.push(t('logic.problem.self'))
          if (a.action === 'set_value' && emptyValue(a.value)) found.push(t('logic.problem.value'))
        }
      }
      if (a.action === 'jump' && conditions[0]) {
        const from = pageOfField(conditions[0].field)
        const to = pages.value.findIndex(p => p.id === target)
        if (to >= 0 && from >= 0 && to <= from) found.push(t('logic.problem.backwards'))
      }
    }
    // The same field both required and hidden by one rule can never be submitted.
    const required = new Set(rule.then.filter(a => a.action === 'require').map(a => a.target))
    if (rule.then.some(a => a.action === 'hide' && required.has(a.target))) found.push(t('logic.problem.conflict'))
    if (!rule.then.length) found.push(t('logic.problem.noAction'))
    return [...new Set(found)]
  }
  const problem = (rule: LogicRule) => problems(rule)[0] ?? null

  // ── Calculated fields, formulas live on the field (props.formula) ───────────────────
  const calculated = computed(() => fields.value.filter(f => f.type === 'calculated'))
  /** Fields a formula can use: numbers, choices (via option numbers), toggles, other calculations. */
  const FORMULA_TYPES = [
    'number', 'currency', 'rating', 'scale', 'slider', 'calculated', 'percentage',
    'dropdown', 'radio', 'checkbox', 'multi_select', 'toggle', 'consent',
  ]
  const formulaSources = computed(() => fields.value.filter(f => FORMULA_TYPES.includes(f.type)))
  function formulaProblem(field: FormField): string | null {
    const formula = String(field.props?.formula ?? '').trim()
    if (!formula) return t('logic.calc.empty')
    const unknown = formulaKeys(formula).find(key => !fields.value.some(f => f.key === key))
    if (unknown) return t('logic.calc.unknown', { key: unknown })
    if (formulaKeys(formula).includes(field.key)) return t('logic.calc.self')
    if (!isValidFormula(formula)) return t('logic.calc.syntax')
    return null
  }

  return {
    rules, fields, sources, pages, fieldById, label, pageLabel, targetsFor,
    addRule, update, removeRule, duplicateRule, moveRule,
    conditionsOf, matchOf, blankCondition, summary, problem, problems, valueText,
    calculated, formulaSources, formulaProblem,
  }
}
