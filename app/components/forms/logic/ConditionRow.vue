<!--
  One "if" line of a rule: question · condition · answer. Column labels show above the first row
  on wider screens; on phones each box is labelled by its placeholder and stacks.
-->
<script setup lang="ts">
import { needsValue, operatorsFor, type LogicCondition, type LogicOperator, type LogicValue } from '#shared/utils/forms/logic'

const props = defineProps<{ condition: LogicCondition; index: number; removable: boolean }>()
const emit = defineEmits<{ update: [patch: Partial<LogicCondition>]; remove: [] }>()
const { t } = useI18n()
const logic = useLogicRules()

const field = computed(() => logic.fieldById.value.get(props.condition.field))
const fieldItems = computed(() =>
  logic.sources.value.map(f => ({ value: f.id, label: logic.label(f), icon: fieldIcon(f.type) })),
)
const operatorItems = computed(() =>
  (field.value ? operatorsFor(field.value.type) : (['eq'] as LogicOperator[])).map(op => ({
    value: op,
    label: t(`logic.op.${op}`),
  })),
)

function pickField(id: string) {
  const next = logic.fieldById.value.get(id)
  const ops = next ? operatorsFor(next.type) : []
  // Keep the comparison when the new question supports it; answers never carry over.
  emit('update', { field: id, op: ops.includes(props.condition.op) ? props.condition.op : (ops[0] ?? 'eq'), value: null, value2: null })
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
      :model-value="condition.field || undefined"
      :items="fieldItems"
      value-key="value"
      :icon="field ? fieldIcon(field.type) : 'i-lucide-circle-help'"
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
        :field="field"
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
