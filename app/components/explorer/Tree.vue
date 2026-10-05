<!--
  The database tree (F12 M3): schemas → tables → columns (names only; types are in Structure), with each table's row count; every
  table has the same square bullet. Search narrows by table name (on the server when the database has more tables than were
  listed) and by the columns already loaded; one table open at a time; a table's columns load when it is opened (lazy, for very
  large databases). Nuxt UI's tree gives keyboard navigation (arrows move and open, Enter selects); picking a table opens it.
-->
<script setup lang="ts">
import type { TreeItem } from '@nuxt/ui'
import type { DatabaseTable, TableColumn } from '#shared/types/destinations'

const props = defineProps<{ tables: DatabaseTable[] | null; columns: Map<string, TableColumn[]>; selected: string | null; loading?: boolean; truncated?: boolean; total?: number }>()
const emit = defineEmits<{ select: [table: DatabaseTable]; expand: [table: DatabaseTable]; search: [q: string] }>()
const { t } = useI18n()
const { number } = useFormat()
const search = ref('')
watch(search, q => emit('search', q))
const keyOf = (table: Pick<DatabaseTable, 'schema' | 'name'>) => `${table.schema}.${table.name}`

const items = computed<TreeItem[]>(() => {
  const q = search.value.trim().toLowerCase()
  const bySchema = new Map<string, TreeItem[]>()
  for (const table of props.tables ?? []) {
    const loaded = props.columns.get(keyOf(table))
    const named = !q || keyOf(table).toLowerCase().includes(q)
    const columns = (loaded ?? []).filter(column => !q || column.name.toLowerCase().includes(q))
    if (!named && !columns.length) continue
    const node: TreeItem = {
      label: table.name,
      key: keyOf(table),
      table,
      defaultExpanded: !named,
      onSelect: () => emit('select', table),
      // Not loaded yet: one "Loading…" row so the table can be opened
      children: !loaded ? [{ label: t('common.loading'), key: `${keyOf(table)}.__loading`, placeholder: true, onSelect: (event: Event) => event.preventDefault() }] : (named ? loaded : columns).map(column => ({
        label: column.name,
        key: `${keyOf(table)}.${column.name}`,
        icon: column.primary ? 'i-lucide-key-round' : 'i-lucide-columns-2',
        column,
        parentTable: { schema: table.schema, name: table.name },
        onSelect: (event: Event) => event.preventDefault(),
      })),
    }
    bySchema.set(table.schema, [...(bySchema.get(table.schema) ?? []), node])
  }
  return [...bySchema].map(([schema, tables]) => ({ label: schema, key: `schema:${schema}`, icon: 'i-lucide-folder-tree', defaultExpanded: true, children: tables, onSelect: (event: Event) => event.preventDefault() }))
})

/** What a tree row is, for the right-click menu (read by ExplorerNavigator). */
const nodeOf = (item: TreeItem) => item.placeholder ? undefined : JSON.stringify(item.column ? { kind: 'column', schema: item.parentTable.schema, table: item.parentTable.name, column: item.column.name } : item.table ? { kind: 'table', schema: item.table.schema, table: item.table.name } : { kind: 'schema', schema: item.label })

// One table open at a time (owner 2026-10-05): opening a table closes the others; schemas stay as they are.
const expanded = ref<string[]>([])
watch(
  () => [search.value, props.tables] as const,
  () => {
    expanded.value = items.value.flatMap(schema => [String(schema.key), ...(schema.children ?? []).filter(table => table.defaultExpanded).map(table => String(table.key))])
  },
  { immediate: true },
)
function onExpanded(keys: string[]) {
  const opened = keys.filter(key => !expanded.value.includes(key) && !key.startsWith('schema:'))
  for (const key of opened) {
    const table = props.tables?.find(item => keyOf(item) === key)
    if (table && !props.columns.has(key)) emit('expand', table)
  }
  expanded.value = opened.length ? keys.filter(key => key.startsWith('schema:') || opened.includes(key)) : keys
}
</script>

<template>
  <div class="flex min-h-0 flex-col gap-2">
    <UInput v-model="search" icon="i-lucide-search" size="xs" :ui="{ base: 'h-7 rounded-sm' }" :placeholder="t('explorer.searchTables')" class="w-full" :aria-label="t('explorer.searchTables')" />
    <div v-if="loading && !tables" class="flex flex-col gap-2"><USkeleton v-for="n in 8" :key="n" class="h-6 rounded-md" :class="n % 3 ? 'ms-5' : ''" /></div>
    <AppEmpty v-else-if="!items.length" size="xs" :icon="search ? 'i-lucide-search-x' : 'i-lucide-database'" :title="search ? t('explorer.noMatch') : t('explorer.noTables')" />
    <UTree v-else :key="search" :items="items" :get-key="item => String(item.key)" :expanded="expanded" color="neutral" size="sm" class="-mx-1 min-h-0 flex-1 overflow-y-auto" @update:expanded="keys => onExpanded(keys as string[])">
      <!-- Every table gets the same square bullet (owner 2026-10-05); schemas and columns keep their icons -->
      <template #item-leading="{ item, ui }">
        <span v-if="item.table" class="flex size-4 shrink-0 items-center justify-center" aria-hidden="true">
          <span class="size-1.5 rounded-[1px] bg-current" :class="keyOf(item.table) === selected ? 'text-highlighted' : 'text-muted'" />
        </span>
        <UIcon v-else-if="item.placeholder" name="i-lucide-loader-circle" class="size-3.5 shrink-0 animate-spin text-muted" />
        <UIcon v-else-if="item.icon" :name="item.icon" :class="ui.linkLeadingIcon()" />
      </template>
      <template #item-label="{ item }">
        <span class="truncate" :data-explorer-node="nodeOf(item)" :title="String(item.label)" :class="[item.table && keyOf(item.table) === selected ? 'font-semibold text-highlighted' : '', item.column ? 'font-mono text-xs' : '', item.placeholder ? 'text-xs text-muted' : '']" dir="ltr">{{ item.label }}</span>
      </template>
      <template #item-trailing="{ item }">
        <span v-if="item.table && item.table.rows_estimate !== null" class="ms-auto ps-2 text-[11px] text-muted tabular-nums">{{ number(item.table.rows_estimate) }}</span>
      </template>
    </UTree>
    <p v-if="items.length && truncated && !search && total" class="px-1 text-[11px] text-muted">{{ t('explorer.treeTruncated', { shown: number(tables?.length ?? 0), n: number(total) }) }}</p>
  </div>
</template>
