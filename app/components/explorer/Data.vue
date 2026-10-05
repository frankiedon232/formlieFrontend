<!--
  A table's rows (F12 M3) in the shared DataView: search across every column, filters for columns
  with few distinct values, sortable headers, Columns (the first eight shown), extra slim rows
  (table only, no grid), server paging. NULL shows dimmed; a row opens the row panel. Exposes the list's params for
  Export.
-->
<script setup lang="ts">
import type { ColumnFacet, TableRow, TableStructure } from '#shared/types/explorer'

const props = defineProps<{ sourceId: string; structure: TableStructure; facets: ColumnFacet[] }>()
const emit = defineEmits<{ open: [row: TableRow, rows: TableRow[]] }>()
const { t } = useI18n()
const api = useApi()

const view = useTemplateRef<{
  refresh: () => Promise<void>
  state: {
    rows: { value: TableRow[] }
    params: () => Record<string, string | number>
    hasActiveFilters: { value: boolean }
  }
  shownColumns: () => string[]
}>('view')
const columns = computed<DataColumn[]>(() =>
  props.structure.columns.map((column, index) => ({
    key: column.name,
    label: column.name,
    sortable: true,
    fixed: index === 0,
    hidden: index >= 8,
    class: 'font-mono',
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
const openRow = (row: TableRow) => emit('open', row, view.value?.state.rows.value ?? [row])
defineExpose({
  refresh: () => view.value?.refresh(),
  params: () => view.value?.state.params() ?? {},
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
    :open-row="openRow"
    :search-placeholder="t('explorer.searchRows')"
    empty-icon="i-lucide-table-2"
    :empty-title="t('explorer.emptyRows')"
    :empty-description="structure.formalie ? t('explorer.emptyResponses') : t('explorer.emptyRowsDesc')"
  >
    <template v-for="column in structure.columns" :key="column.name" #[`${column.name}-cell`]="{ row }">
      <ExplorerCell :value="row.original[column.name]" />
    </template>
  </DataView>
</template>
