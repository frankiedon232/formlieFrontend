<!--
  Step 4: how responses are written: a new row each time, or update the row with the same key;
  answers with several values as JSON or as readable text; choices by value or label; and for a
  new table, which extra facts about each response get a column.
-->
<script setup lang="ts">
import type { DestinationSettings, MetaColumn } from '#shared/types/destinations'

const props = defineProps<{ setup: ReturnType<typeof useStorageSetup>; editing: boolean }>()
const { t } = useI18n()
const s = props.setup
const set = (patch: Partial<DestinationSettings>) => (s.settings.value = { ...s.settings.value, ...patch })
const radio = (name: string, values: string[]) => values.map(value => ({ value, label: t(`destinations.options.${name}.${value}`), description: t(`destinations.options.${name}Desc.${value}`) }))
const keyItems = computed(() => s.columns.value.filter(column => column.source).map(column => ({ value: column.column, label: column.column })))
const EXTRA: MetaColumn[] = ['response_number', 'respondent_email', 'review_status']
const toggle = (key: MetaColumn, on: boolean) => (s.extraMeta.value = on ? [...s.extraMeta.value, key] : s.extraMeta.value.filter(item => item !== key))
// Update-or-insert matches on the column holding the response id unless chosen otherwise.
watch(() => s.settings.value.write_mode, mode => {
  if (mode !== 'upsert') return
  const id = s.columns.value.find(column => column.source?.kind === 'meta' && column.source.key === 'response_id')
  if (id && !keyItems.value.some(item => item.value === s.settings.value.key_column)) set({ key_column: id.column })
})
const ui = { fieldset: 'grid grid-cols-1 gap-3 sm:grid-cols-2', legend: 'mb-2 text-sm font-medium text-highlighted', item: 'items-start has-data-[state=checked]:border-inverted' }
</script>

<template>
  <div class="flex flex-col gap-6">
    <URadioGroup :model-value="s.settings.value.write_mode" :items="radio('write', ['insert', 'upsert'])" variant="card" indicator="end" color="neutral" :legend="t('destinations.options.writeLegend')" :ui="ui" @update:model-value="value => set({ write_mode: value as DestinationSettings['write_mode'] })" />
    <UFormField v-if="s.settings.value.write_mode === 'upsert'" :label="t('destinations.options.keyColumn')" :description="t('destinations.options.keyColumnDesc')">
      <USelect :model-value="s.settings.value.key_column" :items="keyItems" value-key="value" class="w-full font-mono sm:w-80" @update:model-value="value => set({ key_column: String(value) })" />
    </UFormField>
    <URadioGroup :model-value="s.settings.value.multi_value" :items="radio('multi', ['json', 'text'])" variant="card" indicator="end" color="neutral" :legend="t('destinations.options.multiLegend')" :ui="ui" :disabled="editing" @update:model-value="value => set({ multi_value: value as DestinationSettings['multi_value'] })" />
    <URadioGroup :model-value="s.settings.value.choices" :items="radio('choices', ['value', 'label'])" variant="card" indicator="end" color="neutral" :legend="t('destinations.options.choicesLegend')" :ui="ui" @update:model-value="value => set({ choices: value as DestinationSettings['choices'] })" />
    <fieldset v-if="s.mode.value === 'create' && !editing" class="flex flex-col gap-2">
      <legend class="mb-2 text-sm font-medium text-highlighted">{{ t('destinations.options.extraLegend') }}</legend>
      <p class="-mt-1 mb-1 text-xs text-muted">{{ t('destinations.options.extraDesc') }}</p>
      <UCheckbox v-for="key in EXTRA" :key="key" :model-value="s.extraMeta.value.includes(key)" :label="t(`destinations.meta.${key}`)" @update:model-value="value => toggle(key, !!value)" />
    </fieldset>
  </div>
</template>
