<!--
  A table's rows (F12 M3) in the shared DataView: search across every column, filters for columns
  with few distinct values, sortable headers, Columns (the first eight shown), extra slim rows
  (table only, no grid), resizable columns, server paging. NULL shows dimmed; a click opens the row
  panel, a double-click edits the cell in place (ExplorerEditCell). Exposes the list's params for
  Export.
-->
<script setup lang="ts">
import type { ColumnFacet, TableRow, TableStructure } from '#shared/types/explorer'
import { kindOfType, lengthOf } from '#shared/utils/datasources/values'

const props = defineProps<{ sourceId: string; structure: TableStructure; facets: ColumnFacet[]; rowMenu?: (row: TableRow, target: HTMLElement) => ContextMenuGroups }>()
const emit = defineEmits<{ open: [row: TableRow, rows: TableRow[]]; editRow: [row: TableRow] }>()
const { t } = useI18n()
const api = useApi()

const view = useTemplateRef<{
  refresh: () => Promise<void>
  state: {
    rows: { value: TableRow[] }
    params: () => Record<string, string | number>
    hasActiveFilters: { value: boolean }
    query: { value: { page: number; pageSize: number } }
  }
  shownColumns: () => string[]
}>('view')
/** A first width that suits the column's values (people resize from there). */
function startWidth(column: TableStructure['columns'][number]) {
  const kind = kindOfType(column.type)
  if (kind === 'boolean') return 96
  if (kind === 'integer') return column.primary ? 88 : 110
  if (kind === 'decimal' || kind === 'time') return 120
  if (kind === 'date') return 130
  if (kind === 'datetime') return 210
  const length = lengthOf(column.type)
  return !length ? 260 : length <= 32 ? 140 : length <= 100 ? 180 : 220
}
const columns = computed<DataColumn[]>(() =>
  props.structure.columns.map((column, index) => ({
    key: column.name,
    label: column.name,
    sortable: true,
    fixed: index === 0,
    hidden: index >= 8,
    class: 'font-mono',
    width: startWidth(column),
  })),
)
const filters = computed<DataFilter[]>(() =>
  props.facets.map(facet => ({
    key: facet.column,
    label: facet.column,
    icon: 'i-lucide-filter',
    named: true,
    options: facet.values.map(item => ({ value: item.value, label: item.value })),
  })),
)
const fetcher: DataFetcher<TableRow> = (params, signal) =>
  api.list<TableRow>(
    `/datasources/${props.sourceId}/explorer/rows`,
    { ...params, schema: props.structure.schema, table: props.structure.name },
    { signal },
  )
// A click opens the row panel a moment later, so a double-click can edit the cell instead
let pendingOpen: ReturnType<typeof setTimeout> | undefined
const openRow = (row: TableRow) => {
  clearTimeout(pendingOpen)
  pendingOpen = setTimeout(() => emit('open', row, view.value?.state.rows.value ?? [row]), 230)
}
const cancelOpen = () => clearTimeout(pendingOpen)
onBeforeUnmount(cancelOpen)
defineExpose({
  refresh: () => view.value?.refresh(),
  rows: () => view.value?.state.rows.value ?? [],
  // The list's search, filters and sort, plus the page on screen (Export: this page)
  params: () => (view.value ? { ...view.value.state.params(), page: view.value.state.query.value.page, page_size: view.value.state.query.value.pageSize } : {}),
  filtered: () => !!view.value?.state.hasActiveFilters.value || !!view.value?.state.params().q,
})
</script>

<template>
  <DataView
    :id="`explorer:${sourceId}:${structure.schema}.${structure.name}`"
    ref="view"
    :columns="columns"
    :fetcher="fetcher"
    :filters="filters"
    row-key="__key"
    dense
    table-only
    resizable
    :open-row="openRow"
    :row-menu="rowMenu"
    :search-placeholder="t('explorer.searchRows')"
    empty-icon="i-lucide-table-2"
    :empty-title="t('explorer.emptyRows')"
    :empty-description="structure.formalie ? t('explorer.emptyResponses') : t('explorer.emptyRowsDesc')"
  >
    <template v-for="column in structure.columns" :key="column.name" #[`${column.name}-cell`]="{ row }">
      <ExplorerEditCell
        :row="row.original"
        :column="column"
        :structure="structure"
        :source-id="sourceId"
        @start="cancelOpen"
        @long="emit('editRow', row.original)"
        @saved="values => Object.assign(row.original, values)"
      />
    </template>
  </DataView>
</template>
