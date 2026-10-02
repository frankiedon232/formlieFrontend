<!-- Dropdown, multi-select, radio, checkboxes and toggle. Options come from the field (option sets in F13). -->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()
const { t } = useI18n()

const items = computed(() =>
  (props.field.options ?? []).map(option => ({ value: option.value, label: option.label })),
)
const one = computed({
  get: () => (typeof value.value === 'string' ? value.value : undefined),
  set: next => (value.value = next),
})
const many = computed({
  get: () => (Array.isArray(value.value) ? (value.value as string[]) : []),
  set: next => (value.value = next),
})
const on = computed({
  get: () => value.value === true,
  set: next => (value.value = next),
})
const disabled = computed(() => props.mode === 'builder')
</script>

<template>
  <USelect
    v-if="field.type === 'dropdown'"
    :id="id"
    v-model="one"
    :items="items"
    value-key="value"
    :placeholder="field.placeholder || t('renderer.choose')"
    :disabled="disabled"
    class="w-full"
  />
  <USelectMenu
    v-else-if="field.type === 'multi_select'"
    :id="id"
    v-model="many"
    :items="items"
    value-key="value"
    multiple
    :placeholder="field.placeholder || t('renderer.chooseMany')"
    :disabled="disabled"
    class="w-full"
  />
  <URadioGroup
    v-else-if="field.type === 'radio'"
    :id="id"
    v-model="one"
    :items="items"
    color="neutral"
    :disabled="disabled"
    :ui="{ fieldset: 'gap-2' }"
  />
  <UCheckboxGroup
    v-else-if="field.type === 'checkbox'"
    :id="id"
    v-model="many"
    :items="items"
    color="neutral"
    :disabled="disabled"
    :ui="{ fieldset: 'gap-2' }"
  />
  <USwitch
    v-else
    :id="id"
    v-model="on"
    color="neutral"
    :disabled="disabled"
    :label="field.placeholder || undefined"
  />
</template>
