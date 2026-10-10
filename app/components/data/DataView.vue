<!--
  Shared list view (CLAUDE.md rule 6, docs/design table): toolbar · Table ↔ Grid · skeletons ·
  empty / error states · server pagination. URL-synced through useDataView.
  Cells: `#<key>-cell="{ row }"` slots pass straight to UTable; grid cards: `#grid-card="{ row }"`.
-->
<script setup lang="ts" generic="T extends Record<string, any>">
import type { DropdownMenuItem, TableColumn } from '@nuxt/ui'

const props = withDefaults(
  defineProps<{
    id: string
    columns: DataColumn[]
    fetcher: DataFetcher<T>
    filters?: DataFilter[]
    sortOptions?: { label: string; value: string }[]
    defaultSort?: string
    defaultView?: DataViewMode
    dateRange?: boolean
    searchPlaceholder?: string
    selectable?: boolean
    rowKey?: string
    rowActions?: (row: T) => DropdownMenuItem[][]
    /** Row / card whose action is running: dimmed, pulsing and not clickable (CLAUDE.md rule 5). */
    busy?: (row: T) => boolean
    /** Click (or Enter on) a row opens it, e.g. a detail panel (F11 responses). */
    openRow?: (row: T) => void
    /** Right-click on a row or card (owner 2026-10-05); default: Open + the row's ⋯ actions. */
    rowMenu?: (row: T, target: HTMLElement) => ContextMenuGroups
    /** The Columns menu: move and show / hide columns (owner 2026-10-04); on for 4+ columns. */
    columnsMenu?: boolean
    /** Extra slim rows with column lines, for raw data such as database tables (F12 M3). */
    dense?: boolean
    /** Only the table, no Table / Grid switch (raw data such as database rows; owner 2026-10-05). */
    tableOnly?: boolean
    /** Drag the line between headers to resize columns (the database explorer only, owner 2026-10-05). */
    resizable?: boolean
    emptyIcon?: string
    emptyTitle?: string
    emptyDescription?: string
    /** A help article for the empty state (F25 "Learn how"). */
    emptyHelp?: string
  }>(),
  {
    filters: () => [],
    sortOptions: () => [],
    defaultSort: undefined,
    defaultView: 'table',
    searchPlaceholder: undefined,
    rowKey: 'id',
    rowActions: undefined,
    busy: undefined,
    openRow: undefined,
    rowMenu: undefined,
    columnsMenu: undefined,
    dense: false,
    tableOnly: false,
    resizable: false,
    emptyIcon: 'i-lucide-inbox',
    emptyTitle: undefined,
    emptyDescription: undefined,
    emptyHelp: undefined,
  },
)

const TABLE_UI = {
  base: 'min-w-full',
  thead: 'bg-elevated/50',
  th: 'py-2 text-default font-medium',
  td: 'py-3 text-default',
  tr: 'transition-colors hover:bg-elevated/50 data-[selectable=true]:cursor-pointer data-[selected=true]:bg-elevated/50',
}
const DENSE_TABLE_UI = {
  ...TABLE_UI,
  th: 'h-8 px-3 py-0 text-xs text-default font-medium border-e border-default last:border-e-0 whitespace-nowrap',
  td: 'h-7 px-3 py-0 text-xs text-default border-e border-default last:border-e-0 whitespace-nowrap',
}

const tableUi = computed(() => {
  const base = props.dense ? DENSE_TABLE_UI : TABLE_UI
  return props.resizable ? { ...base, base: 'table-fixed w-(--dv-table-w)' } : base
})

const slots = defineSlots<
  {
    'grid-card'?(props: { row: T; columns: string[] }): unknown
    'empty-actions'?(): unknown
    'bulk-actions'?(props: { selected: T[]; clear: () => void }): unknown
    'toolbar-end'?(): unknown
    'toolbar-start'?(): unknown
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- `#<key>-cell` slots receive TanStack cell context, forwarded untouched to UTable
  } & Record<string, ((props: any) => unknown) | undefined>
>()

const { t } = useI18n()
const { messageFor } = useErrorHandler()
const UButton = resolveComponent('UButton')
const UCheckbox = resolveComponent('UCheckbox')
const UDropdownMenu = resolveComponent('UDropdownMenu')

const state = useDataView<T>({
  id: props.id,
  fetcher: props.fetcher,
  filters: () => props.filters,
  defaultSort: props.defaultSort,
  defaultView: props.defaultView,
})
const viewMode = computed(() => (props.tableOnly ? 'table' : state.view.value))

// ── Column order and visibility (remembered per list on this browser) ───────────────────
const layout = useLocalStorage<{ order: string[]; hidden: string[]; shown: string[] }>(`formalie:columns:${props.id}`, { order: [], hidden: [], shown: [] }, { mergeDefaults: true })
const columnOrder = computed(() => {
  const keys = props.columns.map(column => column.key)
  const known = layout.value.order.filter(key => keys.includes(key))
  return [...known, ...keys.filter(key => !known.includes(key))]
})
const isVisible = (column: DataColumn) =>
  !!column.fixed || (layout.value.shown.includes(column.key) ? true : layout.value.hidden.includes(column.key) ? false : !column.hidden)
const orderedColumns = computed(() => {
  const byKey = new Map(props.columns.map(column => [column.key, column]))
  return columnOrder.value.map(key => byKey.get(key)!).filter(isVisible)
})
const showColumnsMenu = computed(() => props.columnsMenu ?? props.columns.length > 3)
function toggleColumn(key: string, on: boolean) {
  const { hidden, shown } = layout.value
  layout.value = { ...layout.value, hidden: on ? hidden.filter(k => k !== key) : [...new Set([...hidden, key])], shown: on ? [...new Set([...shown, key])] : shown.filter(k => k !== key) }
}
const resetColumns = () => {
  layout.value = { order: [], hidden: [], shown: [] }
  columnWidths?.reset()
}

const HIDE = { sm: 'hidden sm:table-cell', md: 'hidden md:table-cell', lg: 'hidden lg:table-cell' }

function sortHeader(column: DataColumn) {
  const sort = state.query.value.sort
  const direction = sort === column.key ? 'asc' : sort === `-${column.key}` ? 'desc' : null
  return h(UButton, {
    label: column.label,
    color: 'neutral',
    variant: 'ghost',
    size: 'sm',
    class: '-mx-2.5 font-medium text-default',
    trailingIcon:
      direction === 'asc'
        ? 'i-lucide-arrow-up'
        : direction === 'desc'
          ? 'i-lucide-arrow-down'
          : 'i-lucide-chevrons-up-down',
    'aria-label': t('dataView.sortBy', { name: column.label }),
    onClick: () => state.setSort(direction === 'asc' ? `-${column.key}` : column.key),
  })
}

const rowSelection = ref<Record<string, boolean>>({})
watch(
  () => state.rows.value,
  () => (rowSelection.value = {}),
)
const selectedRows = computed(() =>
  state.rows.value.filter(row => rowSelection.value[String(row[props.rowKey])]),
)

// Resizable columns (explorer): widths per list, a fixed table layout so they hold
const tableRoot = useTemplateRef<HTMLElement>('root')
const columnWidths = props.resizable ? useColumnWidths(props.id, tableRoot) : null
const px = (value: number) => `${value}px`

const tableColumns = computed<TableColumn<T>[]>(() => {
  const columns: TableColumn<T>[] = orderedColumns.value.map(column => {
    const classes = [column.hideBelow && HIDE[column.hideBelow], column.class].filter(Boolean).join(' ')
    if (!columnWidths)
      return {
        accessorKey: column.key,
        id: column.key,
        header: column.sortable ? () => sortHeader(column) : column.label,
        meta: { class: { th: classes, td: classes } },
      }
    const size = columnWidths.sizeOf(column.key, column.width)
    const width = px(size)
    return {
      accessorKey: column.key,
      id: column.key,
      size,
      minSize: COLUMN_WIDTH.min,
      maxSize: COLUMN_WIDTH.max,
      header: ({ header }) => columnWidths.withHandle(column.key, column.label, header, column.sortable ? sortHeader(column) : column.label),
      meta: { class: { th: `relative ${classes}`, td: `overflow-hidden ${classes}` }, style: { th: { width }, td: { width, maxWidth: width } } },
    }
  })
  if (props.selectable) {
    columns.unshift({
      id: 'select',
      header: ({ table }) =>
        h(UCheckbox, {
          modelValue: table.getIsSomePageRowsSelected() ? 'indeterminate' : table.getIsAllPageRowsSelected(),
          'onUpdate:modelValue': (value: boolean | 'indeterminate') =>
            table.toggleAllPageRowsSelected(!!value),
          'aria-label': t('dataView.selectAll'),
        }),
      cell: ({ row }) =>
        h(UCheckbox, {
          modelValue: row.getIsSelected(),
          'onUpdate:modelValue': (value: boolean | 'indeterminate') => row.toggleSelected(!!value),
          'aria-label': t('dataView.selectRow'),
        }),
      meta: { class: { th: 'w-10', td: 'w-10' } },
    })
  }
  if (props.rowActions) {
    columns.push({
      id: 'actions',
      header: () => h('span', { class: 'sr-only' }, t('dataView.actions')),
      cell: ({ row }) =>
        h(UDropdownMenu, { items: props.rowActions!(row.original), content: { align: 'end' } }, () =>
          h(UButton, {
            icon: 'i-lucide-ellipsis',
            color: 'neutral',
            variant: 'outline',
            size: 'xs',
            square: true,
            'aria-label': t('dataView.actions'),
          }),
        ),
      meta: { class: { th: 'w-12 text-end', td: 'w-12 text-end' } },
    })
  }
  return columns
})

const cellSlots = computed(() =>
  Object.keys(slots).filter(name => name.endsWith('-cell') || name.endsWith('-header')),
)
const BUSY_ROW = 'pointer-events-none opacity-50 motion-safe:animate-pulse'
const tableMeta = computed(() => ({
  class: { tr: (row: { original: T }) => (props.busy?.(row.original) ? BUSY_ROW : '') },
}))

/** A card opens its item when clicked anywhere except its own buttons, links, inputs and menus. */
function openFromCard(event: MouseEvent, row: T) {
  if (!props.openRow || (event.target as HTMLElement).closest('a, button, input, label, select, textarea, [role="menu"], [role="menuitem"]')) return
  props.openRow(row)
}

const showSkeleton = computed(() => state.loading.value && !state.loaded.value)
const isEmpty = computed(() => state.loaded.value && !state.error.value && state.rows.value.length === 0)

// Right-click on a row or a card: its own menu (the app's items follow, AppContextMenu)
const root = tableRoot
useContextMenu().register(root, target => {
  const card = target.closest('[data-row-index]')
  const tr = card ? null : target.closest('tbody tr')
  const row = card ? state.rows.value[Number(card.getAttribute('data-row-index'))] : tr?.parentElement ? state.rows.value[[...tr.parentElement.children].indexOf(tr)] : undefined
  if (!row) return null
  if (props.rowMenu) return props.rowMenu(row, target)
  return [
    ...(props.openRow && !props.rowActions ? [[{ label: t('contextMenu.open'), icon: 'i-lucide-square-arrow-out-up-right', onSelect: () => props.openRow!(row) }]] : []),
    ...((props.rowActions?.(row) ?? []) as ContextMenuGroups),
  ]
})

defineExpose({ refresh: state.refresh, state, shownColumns: () => orderedColumns.value.map(column => column.key) })
</script>

<template>
  <section ref="root" class="flex flex-col gap-4">
    <DataToolbar
      :state="state as DataViewState<unknown>"
      :search-placeholder="searchPlaceholder"
      :sort-options="sortOptions"
      :date-range="dateRange"
      :views="!tableOnly"
    >
      <template v-if="slots['toolbar-start']" #start>
        <slot name="toolbar-start" />
      </template>
      <template v-if="slots['toolbar-end'] || (showColumnsMenu && viewMode === 'table')" #end>
        <slot name="toolbar-end" />
        <DataColumns
          v-if="showColumnsMenu && viewMode === 'table'"
          :columns="columns"
          :order="columnOrder"
          :visible="isVisible"
          @order="keys => (layout = { ...layout, order: keys })"
          @toggle="toggleColumn"
          @reset="resetColumns"
        />
      </template>
    </DataToolbar>

    <div
      v-if="selectable && selectedRows.length"
      class="flex flex-wrap items-center gap-2 rounded-md border border-default bg-elevated/50 px-3 py-2 text-sm"
    >
      <span class="font-medium text-highlighted">{{
        t('dataView.selected', { count: selectedRows.length })
      }}</span>
      <slot name="bulk-actions" :selected="selectedRows" :clear="() => (rowSelection = {})" />
      <UButton
        :label="t('dataView.clearSelection')"
        color="neutral"
        variant="link"
        size="sm"
        class="ms-auto"
        @click="rowSelection = {}"
      />
    </div>

    <AppEmpty
      v-if="state.error.value"
      icon="i-lucide-cloud-alert"
      :title="t('dataView.errorTitle')"
      :description="messageFor(state.error.value)"
      :actions="[
        {
          label: t('common.retry'),
          icon: 'i-lucide-rotate-cw',
          color: 'neutral',
          variant: 'outline',
          onClick: () => state.refresh(),
        },
      ]"
      variant="outline"
    />

    <AppEmpty
      v-else-if="isEmpty"
      :icon="state.hasActiveFilters.value ? 'i-lucide-search-x' : emptyIcon"
      :title="
        state.hasActiveFilters.value ? t('dataView.noResults') : (emptyTitle ?? t('dataView.noResults'))
      "
      :description="state.hasActiveFilters.value ? t('dataView.noResultsDesc') : emptyDescription"
      :help="state.hasActiveFilters.value ? undefined : emptyHelp"
      :actions="
        state.hasActiveFilters.value
          ? [
              {
                label: t('dataView.clearAll'),
                icon: 'i-lucide-x',
                color: 'neutral',
                variant: 'outline',
                onClick: () => state.reset(),
              },
            ]
          : undefined
      "
      variant="outline"
    >
      <template v-if="!state.hasActiveFilters.value && slots['empty-actions']" #actions>
        <slot name="empty-actions" />
      </template>
    </AppEmpty>

    <template v-else-if="viewMode === 'grid'">
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4" :aria-busy="state.loading.value">
        <template v-if="showSkeleton">
          <USkeleton v-for="n in 8" :key="n" class="h-40 rounded-lg" />
        </template>
        <template v-else>
          <div
            v-for="(row, rowIndex) in state.rows.value"
            :key="String(row[rowKey])"
            :data-row-index="rowIndex"
            class="h-full"
            :class="[state.loading.value ? 'opacity-60' : busy?.(row) ? BUSY_ROW : '', openRow ? 'cursor-pointer' : '']"
            :aria-busy="busy?.(row) || undefined"
            @click="openFromCard($event, row)"
          >
            <slot name="grid-card" :row="row" :columns="orderedColumns.map(column => column.key)">
              <UCard>{{ row[columns[0]!.key] }}</UCard>
            </slot>
          </div>
        </template>
      </div>
    </template>

    <div v-else class="overflow-x-auto rounded-lg border border-default">
      <div v-if="showSkeleton" class="divide-y divide-default" :aria-label="t('common.loading')">
        <div class="h-10 bg-elevated/50" />
        <div v-for="n in 8" :key="n" class="flex items-center gap-4 px-4" :class="dense ? 'py-2' : 'py-3.5'">
          <USkeleton class="h-4 w-1/3" />
          <USkeleton class="hidden h-4 w-20 sm:block" />
          <USkeleton class="hidden h-4 w-24 md:block" />
          <USkeleton class="ms-auto h-4 w-16" />
        </div>
      </div>
      <UTable
        v-else
        v-model:row-selection="rowSelection"
        :data="state.rows.value"
        :columns="tableColumns"
        :loading="state.loading.value"
        loading-color="neutral"
        :get-row-id="(row: T) => String(row[rowKey])"
        :meta="tableMeta"
        :on-select="openRow ? (_: Event, row: { original: T }) => openRow!(row.original) : undefined"
        sticky
        :ui="tableUi"
        :column-sizing="columnWidths ? columnWidths.widths.value : undefined"
        :column-sizing-options="columnWidths ? { enableColumnResizing: true, columnResizeMode: 'onChange' } : undefined"
        :style="columnWidths ? { '--dv-table-w': px(columnWidths.total(orderedColumns)) } : undefined"
        @update:column-sizing="value => columnWidths && value && (columnWidths.widths.value = value)"
      >
        <template v-for="name in cellSlots" :key="name" #[name]="slotProps">
          <slot :name="name" v-bind="slotProps" />
        </template>
      </UTable>
    </div>

    <DataPagination
      v-if="state.meta.value && state.meta.value.total > 0 && !state.error.value"
      :meta="state.meta.value"
      @page="state.setPage"
      @page-size="state.setPageSize"
    />
  </section>
</template>
