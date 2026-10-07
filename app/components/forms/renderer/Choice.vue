<!-- Dropdown, multi-select, radio, checkboxes and toggle. Options come from the field; a level of a list with levels shows only what is under the choice above (F15 M2). -->
<script setup lang="ts">
import { isLocked, type FormField } from '#shared/utils/forms/build'
import { cascadeOptions } from '#shared/utils/forms/cascade'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()
const { t } = useI18n()
// Size and style follow the form theme (F8); plain defaults elsewhere.
const control = useControlStyle()

// A level of a list with levels offers only what sits under the choice above (F15 M2)
// (the form hides a level with nothing to offer; the builder canvas keeps it, locked, saying what to choose first)
const live = inject(RENDERER_ANSWERS, null)
const cascading = computed(() => !!live && !!props.field.option_parent)
const items = computed(() =>
  (cascading.value ? cascadeOptions(props.field, live!.fieldsById.value, live!.answers.value) : (props.field.options ?? [])).map(option => ({ value: option.value, label: option.label })),
)
const closed = computed(() => cascading.value && !items.value.length)
const above = computed(() => (props.field.option_parent ? live?.fieldsById.value.get(props.field.option_parent)?.label : '') || t('builder.untitled'))
const placeholder = (fallback: string) => (closed.value ? t('renderer.chooseAboveFirst', { name: above.value }) : props.field.placeholder || fallback)
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
const icon = useFieldIcon(() => props.field)
// Read-only and disabled both block changes here (Nuxt UI choice controls have no read-only state).
const disabled = computed(() => isLocked(props.field) || closed.value)
</script>

<template>
  <USelect
    v-if="field.type === 'dropdown'"
    v-bind="control"
    :id="id"
    v-model="one"
    :items="items"
    value-key="value"
    :placeholder="placeholder(t('renderer.choose'))"
    :icon="icon"
    :disabled="disabled"
    class="w-full"
  />
  <USelectMenu
    v-else-if="field.type === 'multi_select'"
    v-bind="control"
    :id="id"
    v-model="many"
    :items="items"
    value-key="value"
    multiple
    :placeholder="placeholder(t('renderer.chooseMany'))"
    :icon="icon"
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
    :aria-label="field.label"
  />
</template>
