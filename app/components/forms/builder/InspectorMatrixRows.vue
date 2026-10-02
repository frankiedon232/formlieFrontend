<!-- Matrix rows (the questions down the side); columns are the field's options. -->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ field: FormField }>()
const { t } = useI18n()
const builder = useBuilder()
const rows = computed<string[]>(() => (props.field.props?.rows as string[] | undefined) ?? [])
const setRows = (next: string[]) => builder.updateProps(props.field.id, { rows: next }, `rows:${props.field.id}`)
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <h3 class="mt-2 text-xs font-medium text-muted uppercase">{{ t('builder.inspector.rows') }}</h3>
    <div v-for="(row, index) in rows" :key="index" class="flex items-center gap-1">
      <UInput
        :model-value="row"
        size="sm"
        class="min-w-0 flex-1"
        :aria-label="t('builder.inspector.rowN', { n: index + 1 })"
        @update:model-value="v => setRows(rows.map((r, i) => (i === index ? String(v) : r)))"
      />
      <UButton
        icon="i-lucide-x"
        color="neutral"
        variant="ghost"
        size="xs"
        square
        :aria-label="t('builder.inspector.removeRow', { n: index + 1 })"
        @click="setRows(rows.filter((_, i) => i !== index))"
      />
    </div>
    <UButton
      :label="t('builder.inspector.addRow')"
      icon="i-lucide-plus"
      color="neutral"
      variant="outline"
      size="sm"
      class="self-start"
      @click="setRows([...rows, t('builder.defaults.row', { n: rows.length + 1 })])"
    />
  </div>
</template>
