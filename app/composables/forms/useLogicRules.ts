import { allFields, newId, type FormField } from '#shared/utils/forms/build'
import { isInputField } from '#shared/utils/forms/fields'
import { formulaKeys, needsValue, operatorsFor, type LogicAction, type LogicCondition, type LogicRule } from '#shared/utils/forms/logic'

/**
 * The logic editor's model on top of the builder schema: rule CRUD (every change is one undo
 * step), the plain-language summary ("When Severity is High, require Photos.") and the checks
 * that flag broken rules (a field or page that was deleted).
 */
export function useLogicRules() {
  const { t } = useI18n()
  const builder = useBuilder()

  const rules = computed<LogicRule[]>(() => (builder.schema.value?.logic ?? []) as LogicRule[])
  const fields = computed(() => (builder.schema.value ? allFields(builder.schema.value) : []))
  /** Fields a condition can test (answers exist), in form order. */
  const sources = computed(() => fields.value.filter(f => isInputField(f.type) && f.type !== 'calculated'))
  const pages = computed(() => builder.schema.value?.pages ?? [])
  const fieldById = computed(() => new Map(fields.value.map(f => [f.id, f])))
  const label = (f: FormField | undefined) => f?.label?.trim() || (f ? t('builder.untitled') : t('logic.missing'))
  const pageLabel = (id: string) => {
    const i = pages.value.findIndex(p => p.id === id)
    return i < 0 ? t('logic.missing') : pages.value[i]!.title || t('builder.page.default', { n: i + 1 })
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

  function addRule(): string {
    const id = newId('rule')
    const target = fields.value.find(f => f.id !== sources.value[0]?.id)
    mutate(list => list.push({ id, when: { all: [blankCondition()] }, then: [{ action: 'show', target: target?.id ?? '' }] }))
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

  /** Human answer for a condition value (option label, formatted date …). */
  function valueText(condition: LogicCondition) {
    const field = fieldById.value.get(condition.field)
    const option = field?.options?.find(o => o.value === condition.value)
    return option?.label ?? String(condition.value ?? '…')
  }
  function conditionText(c: LogicCondition) {
    return t(`logic.sentence.${c.op}`, { field: label(fieldById.value.get(c.field)), value: needsValue(c.op) ? valueText(c) : '' })
  }
  function actionText(a: { action: LogicAction; target: string }) {
    const target = a.action === 'jump' ? pageLabel(a.target) : label(fieldById.value.get(a.target))
    return t(`logic.sentence.${a.action}`, { target })
  }
  function summary(rule: LogicRule) {
    const join = matchOf(rule) === 'any' ? t('logic.or') : t('logic.and')
    return t('logic.sentence.rule', {
      conditions: conditionsOf(rule).map(conditionText).join(join),
      actions: rule.then.map(actionText).join(t('logic.listJoin')),
    })
  }

  /** What's wrong with a rule, or null (deleted field / page, missing value). */
  function problem(rule: LogicRule): string | null {
    for (const c of conditionsOf(rule)) {
      if (!fieldById.value.has(c.field)) return t('logic.problem.field')
      if (needsValue(c.op) && (c.value == null || c.value === '')) return t('logic.problem.value')
    }
    for (const a of rule.then) {
      const ok = a.action === 'jump' ? pages.value.some(p => p.id === a.target) : fieldById.value.has(a.target)
      if (!ok) return t('logic.problem.target')
    }
    return rule.then.length ? null : t('logic.problem.noAction')
  }

  // Calculated fields — formulas live on the field (props.formula).
  const calculated = computed(() => fields.value.filter(f => f.type === 'calculated'))
  const numericKeys = computed(() =>
    fields.value.filter(f => ['number', 'currency', 'rating', 'scale', 'slider', 'calculated'].includes(f.type)).map(f => f.key),
  )
  function formulaProblem(field: FormField): string | null {
    const formula = String(field.props?.formula ?? '').trim()
    if (!formula) return t('logic.calc.empty')
    const unknown = formulaKeys(formula).find(key => !fields.value.some(f => f.key === key))
    if (unknown) return t('logic.calc.unknown', { key: unknown })
    if (formulaKeys(formula).includes(field.key)) return t('logic.calc.self')
    return null
  }

  return {
    rules, fields, sources, pages, fieldById, label, pageLabel,
    addRule, update, removeRule, duplicateRule, moveRule,
    conditionsOf, matchOf, blankCondition, summary, problem,
    calculated, numericKeys, formulaProblem,
  }
}
