<!--
  One "if" line of a rule: question · condition · answer. Column labels show above the first row
  on wider screens; on phones each box is labelled by its placeholder and stacks. A question from a list
  with details also offers each detail ("Product · Price", leftovers L1): the rule then tests that detail.
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'
import { fieldKind, needsValue, operatorsFor, operatorsForDetail, type LogicCondition, type LogicOperator, type LogicValue } from '#shared/utils/forms/logic'

const props = defineProps<{ condition: LogicCondition; index: number; removable: boolean }>()
const emit = defineEmits<{ update: [patch: Partial<LogicCondition>]; remove: [] }>()
const { t } = useI18n()
const logic = useLogicRules()

// A detail is picked as "{field id}::{column}" from the same list as the questions
const SEP = '::'
const field = computed(() => logic.fieldById.value.get(props.condition.field))
const fieldItems = computed(() =>
  logic.sources.value.flatMap(f => [
    { value: f.id, label: logic.label(f), icon: fieldIcon(f.type) },
    ...logic.detailsOf(f).map(d => ({ value: `${f.id}${SEP}${d.key}`, label: `${logic.label(f)} · ${d.label}`, icon: 'i-lucide-tag' })),
  ]),
)
const picked = computed(() => (props.condition.detail ? `${props.condition.field}${SEP}${props.condition.detail}` : props.condition.field || undefined))
const operatorsOf = (f: FormField | undefined, detail?: string): LogicOperator[] => {
  if (!f) return ['eq']
  if (!detail) return operatorsFor(f.type)
  return operatorsForDetail(!!logic.detailsOf(f).find(d => d.key === detail)?.numeric, fieldKind(f.type) === 'multi')
}
const operatorItems = computed(() => operatorsOf(field.value, props.condition.detail).map(op => ({ value: op, label: t(`logic.op.${op}`) })))
/** What the answer box works with: the question, or for a detail a number or a text. */
const valueField = computed<FormField | undefined>(() => {
  if (!field.value || !props.condition.detail) return field.value
  const numeric = !!logic.detailsOf(field.value).find(d => d.key === props.condition.detail)?.numeric
  return { id: field.value.id, key: field.value.key, label: field.value.label, type: numeric ? 'number' : 'short_text' }
})

function pickField(choice: string) {
  const [id, detail] = choice.split(SEP) as [string, string | undefined]
  const ops = operatorsOf(logic.fieldById.value.get(id), detail)
  // Keep the comparison when the new question supports it; answers never carry over.
  emit('update', { field: id, detail: detail || undefined, op: ops.includes(props.condition.op) ? props.condition.op : (ops[0] ?? 'eq'), value: null, value2: null })
}
function pickOperator(op: LogicOperator) {
  // Switching between one value and a list (or a range) starts the answer fresh.
  const shape = (o: LogicOperator) => (['in', 'not_in', 'contains_all'].includes(o) ? 'list' : o.includes('between') ? 'range' : 'one')
  emit('update', shape(op) === shape(props.condition.op) ? { op } : { op, value: null, value2: null })
}
const setValue = (value: LogicValue, value2?: string | number | null) => emit('update', { value, value2 })
</script>

<template>
  <div class="grid grid-cols-[minmax(0,1fr)_auto] gap-2 sm:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1.3fr)_auto] sm:items-center">
    <USelectMenu
      :model-value="picked"
      :items="fieldItems"
      value-key="value"
      :icon="condition.detail ? 'i-lucide-tag' : field ? fieldIcon(field.type) : 'i-lucide-circle-help'"
      :placeholder="t('logic.pickField')"
      :search-input="{ placeholder: t('common.search') }"
      :aria-label="t('logic.conditionField', { n: index + 1 })"
      class="col-start-1 w-full sm:col-start-auto"
      @update:model-value="v => v && pickField(String(v))"
    />
    <USelect
      :model-value="condition.op"
      :items="operatorItems"
      :aria-label="t('logic.conditionOperator', { n: index + 1 })"
      class="col-start-1 w-full sm:col-start-auto"
      @update:model-value="v => pickOperator(v as LogicOperator)"
    />
    <div class="col-start-1 min-w-0 sm:col-start-auto">
      <FormsLogicValueInput
        v-if="needsValue(condition.op)"
        :field="valueField"
        :op="condition.op"
        :value="condition.value"
        :value2="condition.value2"
        :label="t('logic.conditionValue', { n: index + 1 })"
        @update="setValue"
      />
      <p v-else class="hidden px-1 text-xs text-muted sm:block">{{ t('logic.noValueNeeded') }}</p>
    </div>
    <UButton
      icon="i-lucide-x"
      color="neutral"
      variant="ghost"
      square
      :disabled="!removable"
      :aria-label="t('logic.removeCondition', { n: index + 1 })"
      class="col-start-2 row-start-1 justify-self-end sm:col-start-auto sm:row-start-auto"
      @click="emit('remove')"
    />
  </div>
</template>
