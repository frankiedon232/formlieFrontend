<!--
  Option list editor → Details (F15 M4): up to 10 columns of details every option may carry (postcode,
  price, manager …). In a form, choosing an option can fill other fields with them (field settings →
  Fill other fields). Removing a column removes its details (asked first when some are filled in).
-->
<script setup lang="ts">
import type { OptionColumn, OptionItem } from '#shared/types/forms'
import { uniqueValue, valueFromLabel } from '#shared/utils/forms/options'

const columns = defineModel<OptionColumn[] | null>('columns', { required: true })
const options = defineModel<OptionItem[]>('options', { required: true })
const { t } = useI18n()
const confirm = useConfirm()

const MAX = 10
const filled = (key: string) => options.value.filter(option => option.attrs?.[key] !== undefined && option.attrs[key] !== '').length
const keyFor = (label: string) => uniqueValue(valueFromLabel(label).replace(/^[^a-z]+/, '') || 'detail', (columns.value ?? []).map(item => item.key))

function add() {
  const list = columns.value ?? []
  if (list.length >= MAX) return
  const label = t('optionSets.columns.nameN', { n: list.length + 1 })
  columns.value = [...list, { key: keyFor(label), label }]
}
const rename = (index: number, label: string) => columns.value && (columns.value = columns.value.map((item, i) => (i === index ? { ...item, label } : item)))
async function remove(index: number) {
  const column = columns.value?.[index]
  if (!column) return
  const count = filled(column.key)
  if (count && !(await confirm({ title: t('optionSets.columns.removeTitle', { name: column.label }), description: t('optionSets.columns.removeDesc', { n: count }, count), confirmLabel: t('optionSets.columns.remove'), danger: true }))) return
  const left = columns.value!.filter((_, i) => i !== index)
  columns.value = left.length ? left : null
  options.value = options.value.map(option => {
    if (!option.attrs || !(column.key in option.attrs)) return option
    const attrs = Object.fromEntries(Object.entries(option.attrs).filter(([key]) => key !== column.key))
    const { attrs: _attrs, ...rest } = option
    return Object.keys(attrs).length ? { ...rest, attrs } : rest
  })
}
</script>

<template>
  <div class="flex flex-col gap-2 rounded-lg border border-default p-3">
    <div class="flex flex-wrap items-center gap-2">
      <UIcon name="i-lucide-table-properties" class="size-4 shrink-0 text-muted" />
      <div class="flex min-w-0 flex-1 flex-col">
        <span class="text-sm font-medium text-highlighted">{{ t('optionSets.columns.title') }}</span>
        <span class="text-xs text-muted">{{ t('optionSets.columns.hint') }}</span>
      </div>
      <UButton v-if="(columns?.length ?? 0) < MAX" :label="t('optionSets.columns.add')" icon="i-lucide-plus" color="neutral" variant="outline" size="sm" @click="add" />
    </div>
    <ul v-if="columns?.length" class="flex flex-wrap items-center gap-1.5">
      <li v-for="(column, index) in columns" :key="column.key" class="flex items-center gap-1">
        <UInput :model-value="column.label" size="sm" maxlength="60" class="w-40" :aria-label="t('optionSets.columns.nameOf', { n: index + 1 })" :highlight="!column.label.trim()" :color="!column.label.trim() ? 'error' : undefined" @update:model-value="value => rename(index, String(value))">
          <template #trailing><span class="font-mono text-[10px] text-muted">{{ column.key }}</span></template>
        </UInput>
        <UTooltip :text="t('optionSets.columns.remove')">
          <UButton icon="i-lucide-x" color="neutral" variant="ghost" size="xs" :aria-label="t('optionSets.columns.remove')" @click="remove(index)" />
        </UTooltip>
      </li>
    </ul>
  </div>
</template>
