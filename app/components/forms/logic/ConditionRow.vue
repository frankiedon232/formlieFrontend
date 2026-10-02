<!-- One "if" line of a rule: field · operator · value (input fits the field: options, number, date, text). -->
<script setup lang="ts">
import { fieldKind, needsValue, operatorsFor, type LogicCondition, type LogicOperator } from '#shared/utils/forms/logic'

const props = defineProps<{ condition: LogicCondition; index: number; removable: boolean }>()
const emit = defineEmits<{ update: [patch: Partial<LogicCondition>]; remove: [] }>()
const { t } = useI18n()
const logic = useLogicRules()

const field = computed(() => logic.fieldById.value.get(props.condition.field))
const fieldItems = computed(() =>
  logic.sources.value.map(f => ({ value: f.id, label: logic.label(f), icon: fieldIcon(f.type) })),
)
const operatorItems = computed(() =>
  (field.value ? operatorsFor(field.value.type) : (['eq'] as LogicOperator[])).map(op => ({ value: op, label: t(`logic.op.${op}`) })),
)
const kind = computed(() => (field.value ? fieldKind(field.value.type) : 'text'))
const options = computed(() => (field.value?.options ?? []).map(o => ({ value: o.value, label: o.label })))

function pickField(id: string) {
  const next = logic.fieldById.value.get(id)
  const ops = next ? operatorsFor(next.type) : []
  // Keep the operator when the new field supports it; values never carry over between fields.
  emit('update', { field: id, op: ops.includes(props.condition.op) ? props.condition.op : ops[0] ?? 'eq', value: null })
}
</script>

<template>
  <div class="grid grid-cols-[minmax(0,1fr)_auto] gap-2 sm:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1.2fr)_auto] sm:items-center">
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
      @update:model-value="v => emit('update', { op: v as LogicOperator })"
    />
    <template v-if="needsValue(condition.op)">
      <USelectMenu
        v-if="options.length"
        :model-value="condition.value == null ? undefined : String(condition.value)"
        :items="options"
        value-key="value"
        :placeholder="t('logic.pickValue')"
        :aria-label="t('logic.conditionValue', { n: index + 1 })"
        class="col-start-1 w-full sm:col-start-auto"
        @update:model-value="v => emit('update', { value: v == null ? null : String(v) })"
      />
      <UInput
        v-else
        :model-value="condition.value == null ? '' : String(condition.value)"
        :type="kind === 'number' ? 'number' : kind === 'date' ? 'date' : 'text'"
        :placeholder="t('logic.value')"
        :aria-label="t('logic.conditionValue', { n: index + 1 })"
        class="col-start-1 w-full sm:col-start-auto"
        @update:model-value="v => emit('update', { value: v === '' ? null : kind === 'number' ? Number(v) : String(v) })"
      />
    </template>
    <span v-else class="hidden sm:block" />
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
