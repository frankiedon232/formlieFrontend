<!--
  Data sources → Database explorer (F12 M3). Pick a connection; the tree shows its schemas,
  tables (row counts) and columns, Formalie's response tables marked; a table opens with its rows
  (DataView: search, filters, sort, Columns, extra slim rows, paging, a row opens its panel) and its
  structure. Export in the header. The connection and tree take the sidebar's menu column on
  desktop (back arrow to the menu); elsewhere they open from "Tables". A connection that isn't
  working shows its error with Retry and Check connection. `?ds=` and `?object=schema.table` keep
  the place on reload and in shared links.
-->
<script setup lang="ts">
import type { DataSourceRow } from '#shared/types/datasources'
import type { DatabaseTable } from '#shared/types/destinations'
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ColumnFacet, ExplorerColumn, SchemaResult, TableIndex, TableRow, TableStructure } from '#shared/types/explorer'

definePageMeta({ breadcrumb: 'nav.dataExplorer' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const { handle, messageFor } = useErrorHandler()
const { number } = useFormat()
useHead({ title: () => t('nav.dataExplorer') })

const sources = ref<DataSourceRow[] | null>(null)
const dsId = computed(() => (typeof route.query.ds === 'string' ? route.query.ds : null))
const objectKey = computed(() => (typeof route.query.object === 'string' ? route.query.object : null))
const source = computed(() => sources.value?.find(item => item.id === dsId.value) ?? null)
const go = (query: Record<string, string | undefined>) => void router.replace({ query })

onMounted(async () => {
  try {
    sources.value = (
      await api.list<DataSourceRow>('/datasources', { page_size: 100, sort: 'name' })
    ).data.filter(item => item.enabled)
    if (!dsId.value && sources.value.length)
      go({ ds: (sources.value.find(item => item.status === 'connected') ?? sources.value[0])!.id })
  } catch (error) {
    sources.value = []
    handle(error)
  }
})

// Tables of the connection
const tables = ref<DatabaseTable[] | null>(null)
const tablesError = ref<ApiError | null>(null)
const loadingTables = ref(false)
async function loadTables(keep = false) {
  if (!dsId.value) return
  loadingTables.value = true
  tablesError.value = null
  if (!keep) tables.value = null
  try {
    tables.value = (await api.get<DatabaseTable[]>(`/datasources/${dsId.value}/explorer/tables`)).data
  } catch (error) {
    tablesError.value = handle(error, { silent: true })
  } finally {
    loadingTables.value = false
  }
}
watch(dsId, () => void loadTables(), { immediate: true })

// The table opened
const structure = ref<TableStructure | null>(null)
const facets = ref<ColumnFacet[]>([])
const tableError = ref<ApiError | null>(null)
const loadingTable = ref(false)
async function loadTable() {
  structure.value = null
  facets.value = []
  tableError.value = null
  if (!dsId.value || !objectKey.value) return
  const dot = objectKey.value.indexOf('.')
  const query = { schema: objectKey.value.slice(0, dot), table: objectKey.value.slice(dot + 1) }
  loadingTable.value = true
  try {
    const [shape, values] = await Promise.all([
      api.get<TableStructure>(`/datasources/${dsId.value}/explorer/structure`, query),
      api.get<ColumnFacet[]>(`/datasources/${dsId.value}/explorer/facets`, query),
    ])
    structure.value = shape.data
    facets.value = values.data
  } catch (error) {
    tableError.value = handle(error, { silent: true })
  } finally {
    loadingTable.value = false
  }
}
watch([dsId, objectKey], () => void loadTable(), { immediate: true })

const treeOpen = ref(false)
// The connection and tables take the sidebar's menu column (owner 2026-10-05); the rail stays
const takeover = useSidebarTakeover()
takeover.claim(() => t('nav.dataExplorer'), 'i-lucide-table-2')
watch(takeover.shown, shown => shown && (treeOpen.value = false))
function open(table: Pick<DatabaseTable, 'schema' | 'name'>) {
  treeOpen.value = false
  tab.value = 'data'
  go({ ds: dsId.value ?? undefined, object: `${table.schema}.${table.name}` })
}
const openRef = (ref: { schema: string; table: string }) => {
  rowOpen.value = false
  open({ schema: ref.schema, name: ref.table })
}
const navigator = computed(() => ({ sources: sources.value, sourceId: dsId.value, tables: tables.value, selected: objectKey.value, loading: loadingTables.value }))
const tab = ref<'data' | 'structure'>('data')
const tabs = computed(() => [
  { value: 'data', label: t('explorer.tab.data'), icon: 'i-lucide-rows-3' },
  { value: 'structure', label: t('explorer.tab.structure'), icon: 'i-lucide-network' },
])

// Row panel
const row = ref<TableRow | null>(null)
const rows = ref<TableRow[]>([])
const rowOpen = ref(false)
function openRow(item: TableRow, list: TableRow[]) {
  row.value = item
  rows.value = list
  rowOpen.value = true
}

const data = useTemplateRef<{
  refresh: () => Promise<void>
  params: () => Record<string, string | number>
  filtered: () => boolean
}>('data')

// Changing rows (Full access, their own tables)
const confirm = useConfirm()
const toast = useToast()
const formOpen = ref(false)
const editing = ref<TableRow | null>(null)
function editRow(item: TableRow | null) {
  editing.value = item
  formOpen.value = true
}
function saved(item: TableRow) {
  if (rowOpen.value && row.value?.__key === item.__key) row.value = item
  void data.value?.refresh()
}
const deleting = ref(false)
async function removeRow(item: TableRow) {
  if (!dsId.value || !structure.value) return
  if (
    !(await confirm({
      title: t('explorer.deleteTitle', { key: item.__key }),
      description: t('explorer.deleteDesc'),
      confirmLabel: t('explorer.deleteRow'),
      danger: true,
    }))
  )
    return
  deleting.value = true
  try {
    await api.del(`/datasources/${dsId.value}/explorer/rows`, {
      query: { schema: structure.value.schema, table: structure.value.name, key: item.__key },
    })
    toast.add({ title: t('explorer.rowDeleted'), color: 'success', icon: 'i-lucide-circle-check' })
    rowOpen.value = false
    await data.value?.refresh()
  } catch (error) {
    handle(error)
  } finally {
    deleting.value = false
  }
}
// Structure changes (their own tables with Full access, never response tables)
const schema = useTemplateRef<{ addColumn: () => void; editColumn: (column: ExplorerColumn) => void; dropColumn: (column: ExplorerColumn) => void; addIndex: () => void; dropIndex: (index: TableIndex) => void; table: (mode: 'rename' | 'truncate' | 'drop') => void; removing: string | null }>('schema')
const canCreate = computed(() => source.value?.access.other === 'read_write')
const newTableOpen = ref(false)
// The open table's schema first, then the connection's own list, then the rest
const schemas = computed(() => {
  const theirs = [...new Set([...(tables.value ?? []).filter(item => !item.formalie).map(item => item.schema), ...(source.value?.access.schemas ?? [])])]
  const list = theirs.length ? theirs : [...new Set((tables.value ?? []).map(item => item.schema))]
  const first = structure.value?.schema ?? source.value?.access.schemas[0] ?? (tables.value ?? []).find(item => item.formalie)?.schema
  return first && list.includes(first) ? [first, ...list.filter(item => item !== first)] : list
})
const tableMenu = computed<DropdownMenuItem[][]>(() => [
  [
    { label: t('explorer.ddl.addColumn'), icon: 'i-lucide-columns-3', onSelect: () => ((tab.value = 'structure'), schema.value?.addColumn()) },
    { label: t('explorer.ddl.addIndex'), icon: 'i-lucide-list-tree', onSelect: () => ((tab.value = 'structure'), schema.value?.addIndex()) },
    { label: t('explorer.ddl.renameButton'), icon: 'i-lucide-pencil', onSelect: () => schema.value?.table('rename') },
  ],
  [
    { label: t('explorer.ddl.truncateButton'), icon: 'i-lucide-eraser', color: 'error' as const, onSelect: () => schema.value?.table('truncate') },
    { label: t('explorer.ddl.dropButton'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => schema.value?.table('drop') },
  ],
])
async function schemaChanged(result: SchemaResult) {
  await loadTables(true)
  if (!result.table) return go({ ds: dsId.value ?? undefined })
  const key = `${result.table.schema}.${result.table.name}`
  if (key !== objectKey.value) return go({ ds: dsId.value ?? undefined, object: key })
  await loadTable()
  await data.value?.refresh()
}
function tableCreated(table: { schema: string; name: string }) {
  void loadTables(true)
  tab.value = 'structure'
  go({ ds: dsId.value ?? undefined, object: `${table.schema}.${table.name}` })
}
const readOnlyText = computed(() =>
  structure.value?.read_only ? t(`explorer.readOnly.${structure.value.read_only}`) : null,
)
</script>

<template>
  <AppPanel
    id="data-explorer"
    :title="t('nav.dataExplorer')"
    :subtitle="source ? `${source.name} · ${engineName(source.engine)}` : t('dataSources.section.explorer')"
    subtitle-icon="i-lucide-table-2"
  >
    <template #actions>
      <UButton
        v-if="!takeover.shown.value"
        :label="t('explorer.tables')"
        icon="i-lucide-folder-tree"
        color="neutral"
        variant="outline"
        @click="treeOpen = true"
      />
      <UButton
        v-if="canCreate && dsId && !tablesError"
        :label="t('explorer.ddl.newTable')"
        icon="i-lucide-table-2"
        color="neutral"
        variant="outline"
        class="hidden sm:inline-flex"
        @click="newTableOpen = true"
      />
      <template v-if="structure && dsId && !structure.read_only">
        <UButton :label="t('explorer.addRow')" icon="i-lucide-plus" color="neutral" @click="editRow(null)" />
      </template>
      <ExplorerExportButton
        v-if="structure && dsId"
        :source-id="dsId"
        :schema="structure.schema"
        :table="structure.name"
        :params="() => data?.params() ?? {}"
        :filtered="!!data?.filtered()"
      />
    </template>

    <!-- No connections -->
    <UEmpty
      v-if="sources && !sources.length"
      icon="i-lucide-database"
      :title="t('explorer.noConnections')"
      :description="t('explorer.noConnectionsDesc')"
      :actions="[
        {
          label: t('dataSources.add'),
          icon: 'i-lucide-plus',
          color: 'neutral',
          to: '/data-sources/connections/new',
        },
      ]"
      class="my-auto"
    />
    <!-- The connection isn't working -->
    <UEmpty
      v-else-if="tablesError"
      icon="i-lucide-plug-zap"
      :title="t('explorer.cantReach')"
      :description="messageFor(tablesError)"
      :actions="[
        {
          label: t('common.retry'),
          icon: 'i-lucide-rotate-cw',
          color: 'neutral',
          variant: 'outline',
          onClick: () => void loadTables(),
        },
        {
          label: t('explorer.checkConnection'),
          icon: 'i-lucide-activity',
          color: 'neutral',
          to: { path: '/data-sources/connections', query: { connection: dsId } },
        },
      ]"
      class="my-auto"
    />
    <div v-else class="flex min-h-0 min-w-0 flex-1 flex-col">
      <div class="flex min-w-0 flex-col gap-4">
        <UEmpty
          v-if="!objectKey"
          icon="i-lucide-mouse-pointer-click"
          :title="t('explorer.pickTable')"
          :description="t('explorer.pickTableDesc')"
          variant="outline"
          :actions="[
            {
              label: t('explorer.tables'),
              icon: 'i-lucide-folder-tree',
              color: 'neutral',
              variant: 'outline',
              class: takeover.shown.value ? 'hidden' : '',
              onClick: () => (treeOpen = true),
            },
          ]"
        />
        <UEmpty
          v-else-if="tableError"
          icon="i-lucide-cloud-alert"
          :title="t('dataView.errorTitle')"
          :description="messageFor(tableError)"
          :actions="[
            {
              label: t('common.retry'),
              icon: 'i-lucide-rotate-cw',
              color: 'neutral',
              variant: 'outline',
              onClick: () => void loadTable(),
            },
          ]"
          variant="outline"
        />
        <template v-else-if="!structure">
          <USkeleton class="h-20 rounded-lg" />
          <USkeleton class="h-96 rounded-lg" />
        </template>
        <template v-else>
          <!-- The table: one slim line -->
          <div class="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-default px-3 py-2 sm:flex-nowrap">
            <UIcon :name="structure.formalie ? 'i-lucide-inbox' : 'i-lucide-table-2'" class="size-4 shrink-0 text-highlighted" />
            <h2 class="min-w-0 truncate font-mono text-sm font-semibold text-highlighted" dir="ltr">
              <span class="font-normal text-muted">{{ structure.schema }}.</span>{{ structure.name }}
            </h2>
            <UBadge
              :label="structure.formalie ? t('destinations.table.created') : t('destinations.table.yours')"
              color="neutral"
              variant="outline"
              size="sm"
              class="hidden shrink-0 rounded-md md:inline-flex"
            />
            <span class="hidden shrink-0 text-xs whitespace-nowrap text-muted tabular-nums lg:inline">{{
              t('explorer.facts', { rows: number(structure.rows_estimate ?? 0), columns: structure.columns.length })
            }}</span>
            <NuxtLink
              v-if="structure.form"
              :to="`/forms/${structure.form.id}`"
              class="hidden min-w-0 truncate text-xs text-muted underline-offset-2 hover:text-highlighted hover:underline 2xl:inline"
              >{{ t('explorer.formOf', { form: structure.form.name }) }}</NuxtLink
            >
            <UTooltip v-if="readOnlyText" :text="readOnlyText">
              <span class="flex shrink-0 items-center gap-1 text-xs whitespace-nowrap text-muted" tabindex="0" :aria-label="readOnlyText">
                <UIcon name="i-lucide-lock" class="size-3.5 shrink-0" /> {{ t('explorer.readOnlyShort') }}
              </span>
            </UTooltip>
            <UTabs
              v-model="tab"
              :items="tabs"
              :content="false"
              color="neutral"
              size="xs"
              class="shrink-0 sm:ms-auto"
              :ui="{ ...SEGMENTED_UI, root: 'w-full sm:w-fit' }"
            />
            <UDropdownMenu v-if="structure.alterable" :items="tableMenu" :content="{ align: 'end' }">
              <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('explorer.ddl.tableActions', { table: structure.name })" />
            </UDropdownMenu>
          </div>

          <div class="transition-opacity" :class="loadingTable ? 'opacity-60' : ''">
            <ExplorerData
              v-if="tab === 'data' && dsId"
              :key="`${dsId}:${objectKey}`"
              ref="data"
              :source-id="dsId"
              :structure="structure"
              :facets="facets"
              @open="openRow"
            />
            <ExplorerStructure
              v-else
              :structure="structure"
              :removing="schema?.removing"
              @table="openRef"
              @add-column="schema?.addColumn()"
              @edit-column="column => schema?.editColumn(column)"
              @drop-column="column => schema?.dropColumn(column)"
              @add-index="schema?.addIndex()"
              @drop-index="index => schema?.dropIndex(index)"
            />
          </div>
        </template>
      </div>
    </div>

    <Teleport v-if="takeover.shown.value" :to="`#${SIDEBAR_TAKEOVER_ID}`" defer>
      <ExplorerNavigator v-bind="navigator" @source="id => go({ ds: id })" @select="open" />
    </Teleport>
    <USlideover
      v-model:open="treeOpen"
      side="left"
      :title="t('explorer.tables')"
      :ui="{ content: 'w-full max-w-xs', body: 'flex p-0 sm:p-0' }"
    >
      <template #body>
        <ExplorerNavigator v-bind="navigator" @source="id => go({ ds: id })" @select="open" />
      </template>
    </USlideover>
    <ExplorerRowDetail
      v-if="structure"
      v-model:open="rowOpen"
      :row="row"
      :rows="rows"
      :structure="structure"
      :busy="deleting"
      @go="item => (row = item)"
      @table="openRef"
      @edit="editRow"
      @remove="removeRow"
    />
    <ExplorerSchemaActions v-if="structure?.alterable && dsId && source" ref="schema" :source-id="dsId" :engine="source.engine" :structure="structure" @changed="schemaChanged" />
    <ExplorerNewTableModal v-if="canCreate && dsId && source" v-model:open="newTableOpen" :source-id="dsId" :engine="source.engine" :schemas="schemas" @created="tableCreated" />
    <template v-if="structure && dsId && !structure.read_only">
      <ExplorerRowForm
        v-model:open="formOpen"
        :source-id="dsId"
        :structure="structure"
        :row="editing"
        @saved="saved"
      />
    </template>
  </AppPanel>
</template>
