<!--
  The database tree (F12 M3): schemas → tables → columns (type on hover), with each table's row count; Formalie's
  response tables marked. Search narrows by table or column name. Nuxt UI's tree gives keyboard
  navigation (arrows move and open, Enter selects); picking a table opens it.
-->
<script setup lang="ts">
import type { TreeItem } from '@nuxt/ui'
import type { DatabaseTable } from '#shared/types/destinations'

const props = defineProps<{ tables: DatabaseTable[] | null; selected: string | null; loading?: boolean }>()
const emit = defineEmits<{ select: [table: DatabaseTable] }>()
const { t } = useI18n()
const { number } = useFormat()
const search = ref('')
const keyOf = (table: Pick<DatabaseTable, 'schema' | 'name'>) => `${table.schema}.${table.name}`

const items = computed<TreeItem[]>(() => {
  const q = search.value.trim().toLowerCase()
  const bySchema = new Map<string, TreeItem[]>()
  for (const table of props.tables ?? []) {
    const columns = table.columns.filter(column => !q || column.name.toLowerCase().includes(q))
    if (q && !table.name.toLowerCase().includes(q) && !columns.length) continue
    const node: TreeItem = {
      label: table.name,
      key: keyOf(table),
      icon: table.formalie ? 'i-lucide-inbox' : 'i-lucide-table-2',
      table,
      defaultExpanded: !!q && !table.name.toLowerCase().includes(q),
      onSelect: () => emit('select', table),
      children: (q && !table.name.toLowerCase().includes(q) ? columns : table.columns).map(column => ({
        label: column.name,
        key: `${keyOf(table)}.${column.name}`,
        icon: column.primary ? 'i-lucide-key-round' : 'i-lucide-columns-2',
        column,
        onSelect: (event: Event) => event.preventDefault(),
      })),
    }
    bySchema.set(table.schema, [...(bySchema.get(table.schema) ?? []), node])
  }
  return [...bySchema].map(([schema, tables]) => ({ label: schema, key: `schema:${schema}`, icon: 'i-lucide-folder-tree', defaultExpanded: true, children: tables, onSelect: (event: Event) => event.preventDefault() }))
})
</script>

<template>
  <div class="flex min-h-0 flex-col gap-3">
    <UInput v-model="search" icon="i-lucide-search" :placeholder="t('explorer.searchTables')" class="w-full" :aria-label="t('explorer.searchTables')" />
    <div v-if="loading && !tables" class="flex flex-col gap-2"><USkeleton v-for="n in 8" :key="n" class="h-6 rounded-md" :class="n % 3 ? 'ms-5' : ''" /></div>
    <p v-else-if="!items.length" class="px-1 text-sm text-muted">{{ search ? t('explorer.noMatch') : t('explorer.noTables') }}</p>
    <UTree v-else :key="search" :items="items" :get-key="item => String(item.key)" color="neutral" size="sm" class="-mx-1 min-h-0 flex-1 overflow-y-auto">
      <template #item-label="{ item }">
        <span class="truncate" :title="item.column ? `${item.label} · ${item.column.type}` : String(item.label)" :class="[item.table && keyOf(item.table) === selected ? 'font-semibold text-highlighted' : '', item.column ? 'font-mono text-xs' : '']" dir="ltr">{{ item.label }}</span>
      </template>
      <template #item-trailing="{ item }">
        <span v-if="item.table && item.table.rows_estimate !== null" class="ms-auto ps-2 text-[11px] text-muted tabular-nums">{{ number(item.table.rows_estimate) }}</span>
      </template>
    </UTree>
    <p class="mt-auto flex shrink-0 items-center gap-1.5 border-t border-default px-1 pt-2.5 text-[11px] text-muted"><UIcon name="i-lucide-inbox" class="size-3.5" /> {{ t('explorer.responseTable') }}</p>
  </div>
</template>
