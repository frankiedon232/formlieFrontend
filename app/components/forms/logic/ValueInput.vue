<!--
  The value part of a condition (or of "set value"): fits the field and the operator —
  options (one or several), number, date (Nuxt UI date input), yes / no, a count, or a range
  (from … to …). Free text otherwise; several free-text values as tags.
-->
<script setup lang="ts">
import { parseDate, parseTime } from '@internationalized/date'
import type { FormField } from '#shared/utils/forms/build'
import { fieldKind, takesCount, takesList, takesRange, type LogicOperator, type LogicValue } from '#shared/utils/forms/logic'

const props = defineProps<{
  field: FormField | undefined
  op: LogicOperator | 'set'
  value: LogicValue | undefined
  value2?: string | number | null
  label: string
}>()
const emit = defineEmits<{ update: [value: LogicValue, value2?: string | number | null] }>()
const { t } = useI18n()

const kind = computed(() => (props.field ? fieldKind(props.field.type) : 'text'))
const options = computed(() => (props.field?.options ?? []).map(o => ({ value: o.value, label: o.label })))
const many = computed(() => (props.op === 'set' ? kind.value === 'multi' : takesList(props.op)))
const range = computed(() => props.op !== 'set' && takesRange(props.op))
const count = computed(() => props.op !== 'set' && takesCount(props.op))
const isDate = computed(() => kind.value === 'date' && props.field?.type !== 'time')
const listValue = computed(() => (Array.isArray(props.value) ? props.value : props.value == null || props.value === '' ? [] : [String(props.value)]))

const toDate = (v: unknown) => {
  try {
    return typeof v === 'string' && v ? parseDate(v.slice(0, 10)) : undefined
  } catch {
    return undefined
  }
}
const toTime = (v: unknown) => {
  try {
    return typeof v === 'string' && v ? parseTime(v) : undefined
  } catch {
    return undefined
  }
}
const fromInput = (v: unknown) => (v === '' || v == null ? null : kind.value === 'number' ? Number(v) : String(v))
</script>

<template>
  <!-- From … to … -->
  <div v-if="range" class="grid grid-cols-2 gap-2">
    <template v-if="isDate">
      <UInputDate
        :model-value="toDate(value)"
        :aria-label="`${label} — ${t('logic.from')}`"
        class="w-full"
        @update:model-value="v => emit('update', v ? v.toString() : null, value2)"
      />
      <UInputDate
        :model-value="toDate(value2)"
        :aria-label="`${label} — ${t('logic.to')}`"
        class="w-full"
        @update:model-value="v => emit('update', (value as LogicValue) ?? null, v ? v.toString() : null)"
      />
    </template>
    <template v-else>
      <UInput
        type="number"
        :model-value="value == null ? '' : String(value)"
        :placeholder="t('logic.from')"
        :aria-label="`${label} — ${t('logic.from')}`"
        class="w-full"
        @update:model-value="v => emit('update', fromInput(v), value2)"
      />
      <UInput
        type="number"
        :model-value="value2 == null ? '' : String(value2)"
        :placeholder="t('logic.to')"
        :aria-label="`${label} — ${t('logic.to')}`"
        class="w-full"
        @update:model-value="v => emit('update', (value as LogicValue) ?? null, v === '' ? null : Number(v))"
      />
    </template>
  </div>

  <UInputNumber
    v-else-if="count"
    :model-value="value == null || value === '' ? undefined : Number(value)"
    :min="0"
    :max="500"
    :aria-label="label"
    class="w-full"
    @update:model-value="v => emit('update', v ?? null)"
  />

  <USelect
    v-else-if="kind === 'toggle'"
    :model-value="value == null ? undefined : String(value)"
    :items="[{ value: 'true', label: t('logic.yes') }, { value: 'false', label: t('logic.no') }]"
    :placeholder="t('logic.pickValue')"
    :aria-label="label"
    class="w-full"
    @update:model-value="v => emit('update', String(v))"
  />

  <USelectMenu
    v-else-if="options.length"
    :model-value="many ? listValue : value == null ? undefined : String(value)"
    :items="options"
    value-key="value"
    :multiple="many"
    :placeholder="many ? t('logic.pickValues') : t('logic.pickValue')"
    :search-input="{ placeholder: t('common.search') }"
    :aria-label="label"
    class="w-full"
    @update:model-value="v => emit('update', many ? ((v as string[]) ?? []) : v == null ? null : String(v))"
  />

  <UInputTags
    v-else-if="many"
    :model-value="listValue"
    :placeholder="t('logic.typeValues')"
    :aria-label="label"
    class="w-full"
    @update:model-value="v => emit('update', (v as string[]) ?? [])"
  />

  <UInputDate
    v-else-if="isDate"
    :model-value="toDate(value)"
    :aria-label="label"
    class="w-full"
    @update:model-value="v => emit('update', v ? v.toString() : null)"
  />

  <UInputTime
    v-else-if="field?.type === 'time'"
    :model-value="toTime(value)"
    :aria-label="label"
    class="w-full"
    @update:model-value="v => emit('update', v ? v.toString().slice(0, 5) : null)"
  />

  <UInput
    v-else
    :model-value="value == null ? '' : String(value)"
    :type="kind === 'number' ? 'number' : 'text'"
    :placeholder="t('logic.value')"
    :aria-label="label"
    class="w-full"
    @update:model-value="v => emit('update', fromInput(v))"
  />
</template>
