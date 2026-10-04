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
    emptyIcon?: string
    emptyTitle?: string
    emptyDescription?: string
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
    emptyIcon: 'i-lucide-inbox',
    emptyTitle: undefined,
    emptyDescription: undefined,
  },
)

const slots = defineSlots<
  {
    'grid-card'?(props: { row: T }): unknown
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
  filters: props.filters,
  defaultSort: props.defaultSort,
  defaultView: props.defaultView,
})

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

const tableColumns = computed<TableColumn<T>[]>(() => {
  const columns: TableColumn<T>[] = props.columns.map(column => ({
    accessorKey: column.key,
    id: column.key,
    header: column.sortable ? () => sortHeader(column) : column.label,
    meta: {
      class: {
        th: [column.hideBelow && HIDE[column.hideBelow], column.class].filter(Boolean).join(' '),
        td: [column.hideBelow && HIDE[column.hideBelow], column.class].filter(Boolean).join(' '),
      },
    },
  }))
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

const showSkeleton = computed(() => state.loading.value && !state.loaded.value)
const isEmpty = computed(() => state.loaded.value && !state.error.value && state.rows.value.length === 0)

defineExpose({ refresh: state.refresh, state })
</script>

<template>
  <section class="flex flex-col gap-4">
    <DataToolbar
      :state="state as DataViewState<unknown>"
      :search-placeholder="searchPlaceholder"
      :sort-options="sortOptions"
      :date-range="dateRange"
      views
    >
      <template v-if="slots['toolbar-start']" #start>
        <slot name="toolbar-start" />
      </template>
      <template v-if="slots['toolbar-end']" #end>
        <slot name="toolbar-end" />
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

    <UEmpty
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

    <UEmpty
      v-else-if="isEmpty"
      :icon="state.hasActiveFilters.value ? 'i-lucide-search-x' : emptyIcon"
      :title="
        state.hasActiveFilters.value ? t('dataView.noResults') : (emptyTitle ?? t('dataView.noResults'))
      "
      :description="state.hasActiveFilters.value ? t('dataView.noResultsDesc') : emptyDescription"
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
    </UEmpty>

    <template v-else-if="state.view.value === 'grid'">
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4" :aria-busy="state.loading.value">
        <template v-if="showSkeleton">
          <USkeleton v-for="n in 8" :key="n" class="h-40 rounded-lg" />
        </template>
        <template v-else>
          <div
            v-for="row in state.rows.value"
            :key="String(row[rowKey])"
            :class="state.loading.value ? 'opacity-60' : busy?.(row) ? BUSY_ROW : ''"
            :aria-busy="busy?.(row) || undefined"
          >
            <slot name="grid-card" :row="row">
              <UCard>{{ row[columns[0]!.key] }}</UCard>
            </slot>
          </div>
        </template>
      </div>
    </template>

    <div v-else class="overflow-x-auto rounded-lg border border-default">
      <div v-if="showSkeleton" class="divide-y divide-default" :aria-label="t('common.loading')">
        <div class="h-10 bg-elevated/50" />
        <div v-for="n in 8" :key="n" class="flex items-center gap-4 px-4 py-3.5">
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
        :ui="{
          base: 'min-w-full',
          thead: 'bg-elevated/50',
          th: 'py-2 text-default font-medium',
          td: 'py-3 text-default',
          tr: 'data-[selected=true]:bg-elevated/50',
        }"
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
