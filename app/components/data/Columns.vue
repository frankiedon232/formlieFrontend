<!--
  Table columns for every DataView (owner 2026-10-04: "change the position of a column, show or
  hide some"): drag a column by its handle to any position, or use ↑ / ↓ (keyboard); tick to show,
  untick to hide (columns marked fixed always show). Reset brings back the page's own order.
  Remembered per list on this browser (useDataView id).
-->
<script setup lang="ts">
import { VueDraggable } from 'vue-draggable-plus'

const props = defineProps<{ columns: DataColumn[]; order: string[]; visible: (column: DataColumn) => boolean }>()
const emit = defineEmits<{ order: [keys: string[]]; toggle: [key: string, on: boolean]; reset: [] }>()
const { t } = useI18n()

const byKey = computed(() => new Map(props.columns.map(column => [column.key, column])))
const items = computed({
  get: () => props.order.map(key => byKey.value.get(key)!).filter(Boolean),
  set: next => emit('order', next.map(column => column.key)),
})
const shown = computed(() => items.value.filter(props.visible).length)
function move(index: number, by: -1 | 1) {
  const keys = [...props.order]
  const target = index + by
  if (target < 0 || target >= keys.length) return
  ;[keys[index], keys[target]] = [keys[target]!, keys[index]!]
  emit('order', keys)
}
</script>

<template>
  <UPopover :content="{ align: 'end' }">
    <UButton icon="i-lucide-columns-3" :label="t('dataView.columns.button')" color="neutral" variant="outline" :ui="{ label: 'hidden 2xl:inline' }" :aria-label="t('dataView.columns.button')">
      <template #trailing>
        <UBadge :label="`${shown}/${items.length}`" color="neutral" variant="soft" size="sm" class="hidden tabular-nums 2xl:inline-flex" />
      </template>
    </UButton>
    <template #content>
      <div class="flex w-80 flex-col">
        <div class="flex items-center justify-between gap-2 border-b border-default px-3 py-2.5">
          <div class="flex flex-col">
            <span class="text-sm font-semibold text-highlighted">{{ t('dataView.columns.title') }}</span>
            <span class="text-xs text-muted">{{ t('dataView.columns.hint') }}</span>
          </div>
          <UButton :label="t('dataView.columns.reset')" color="neutral" variant="link" size="xs" @click="emit('reset')" />
        </div>
        <VueDraggable v-model="items" handle="[data-column-handle]" :animation="150" class="flex max-h-80 flex-col overflow-y-auto p-1.5" tag="ul">
          <li v-for="(column, index) in items" :key="column.key" class="group flex items-center gap-1.5 rounded-md px-1.5 py-1 hover:bg-elevated/60">
            <UIcon name="i-lucide-grip-vertical" class="size-4 shrink-0 cursor-grab text-dimmed group-hover:text-muted" data-column-handle aria-hidden="true" />
            <UCheckbox
              :model-value="visible(column)"
              :disabled="column.fixed"
              :aria-label="t('dataView.columns.show', { name: column.label })"
              @update:model-value="on => emit('toggle', column.key, !!on)"
            />
            <span class="min-w-0 flex-1 truncate text-sm" :class="visible(column) ? 'text-default' : 'text-muted'">{{ column.label }}</span>
            <UButton icon="i-lucide-chevron-up" color="neutral" variant="ghost" size="xs" square :disabled="index === 0" :aria-label="t('dataView.columns.up', { name: column.label })" class="opacity-60 group-hover:opacity-100 focus-visible:opacity-100" @click="move(index, -1)" />
            <UButton icon="i-lucide-chevron-down" color="neutral" variant="ghost" size="xs" square :disabled="index === items.length - 1" :aria-label="t('dataView.columns.down', { name: column.label })" class="opacity-60 group-hover:opacity-100 focus-visible:opacity-100" @click="move(index, 1)" />
          </li>
        </VueDraggable>
      </div>
    </template>
  </UPopover>
</template>
