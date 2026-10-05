<!--
  Data sources → Database explorer (F12 M3). Pick a connection; the tree shows its schemas,
  tables (row counts) and columns, Formalie's response tables marked; a table opens with its rows
  (DataView: search, filters, sort, Columns, Table / Grid, paging, a row opens its panel) and its
  structure. Export in the header. On phones the tree opens from "Tables". A connection that isn't
  working shows its error with Retry and Check connection. `?ds=` and `?object=schema.table` keep
  the place on reload and in shared links.
-->
<script setup lang="ts">
import type { DataSourceRow } from '#shared/types/datasources'
import type { DatabaseTable } from '#shared/types/destinations'
import type { ColumnFacet, TableRow, TableStructure } from '#shared/types/explorer'

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
const sourceItems = computed(() =>
  (sources.value ?? []).map(item => ({ value: item.id, label: item.name, icon: engineIcon(item.engine) })),
)

// Tables of the connection
const tables = ref<DatabaseTable[] | null>(null)
const tablesError = ref<ApiError | null>(null)
const loadingTables = ref(false)
async function loadTables() {
  if (!dsId.value) return
  loadingTables.value = true
  tablesError.value = null
  tables.value = null
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
function open(table: Pick<DatabaseTable, 'schema' | 'name'>) {
  treeOpen.value = false
  tab.value = 'data'
  go({ ds: dsId.value ?? undefined, object: `${table.schema}.${table.name}` })
}
const openRef = (ref: { schema: string; table: string }) => {
  rowOpen.value = false
  open({ schema: ref.schema, name: ref.table })
}
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
const importOpen = ref(false)
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
      <USelectMenu
        v-if="sources?.length"
        :model-value="dsId ?? undefined"
        :items="sourceItems"
        value-key="value"
        :icon="source ? engineIcon(source.engine) : 'i-lucide-database'"
        class="w-44 sm:w-56"
        :aria-label="t('explorer.connection')"
        @update:model-value="value => go({ ds: String(value) })"
      />
      <UButton
        :label="t('explorer.tables')"
        icon="i-lucide-folder-tree"
        color="neutral"
        variant="outline"
        class="lg:hidden"
        @click="treeOpen = true"
      />
      <template v-if="structure && dsId && !structure.read_only">
        <UButton
          :label="t('explorer.import.button')"
          icon="i-lucide-file-up"
          color="neutral"
          variant="outline"
          class="hidden sm:inline-flex"
          @click="importOpen = true"
        />
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
    <div v-else class="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[17rem_minmax(0,1fr)]">
      <UCard
        variant="outline"
        class="hidden lg:block"
        :ui="{ body: 'flex max-h-[calc(100dvh-10rem)] flex-col p-3' }"
      >
        <ExplorerTree :tables="tables" :selected="objectKey" :loading="loadingTables" @select="open" />
      </UCard>

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
              class: 'lg:hidden',
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
          <!-- The table -->
          <div class="flex flex-wrap items-start gap-3 rounded-lg border border-default p-3 sm:p-4">
            <span class="flex size-10 shrink-0 items-center justify-center rounded-lg border border-default"
              ><UIcon
                :name="structure.formalie ? 'i-lucide-inbox' : 'i-lucide-table-2'"
                class="size-5 text-highlighted"
            /></span>
            <div class="flex min-w-0 flex-1 flex-col gap-1">
              <h2 class="truncate font-mono text-base font-semibold text-highlighted" dir="ltr">
                {{ structure.schema }}.{{ structure.name }}
              </h2>
              <div class="flex flex-wrap items-center gap-1.5 text-xs text-muted">
                <UBadge
                  :label="
                    structure.formalie ? t('destinations.table.created') : t('destinations.table.yours')
                  "
                  color="neutral"
                  variant="outline"
                  size="sm"
                  class="rounded-md"
                />
                <span>{{
                  t('explorer.facts', {
                    rows: number(structure.rows_estimate ?? 0),
                    columns: structure.columns.length,
                  })
                }}</span>
                <NuxtLink
                  v-if="structure.form"
                  :to="`/forms/${structure.form.id}`"
                  class="underline-offset-2 hover:underline"
                  >{{ t('explorer.formOf', { form: structure.form.name }) }}</NuxtLink
                >
              </div>
              <p v-if="readOnlyText" class="flex items-center gap-1.5 text-xs text-muted">
                <UIcon name="i-lucide-lock" class="size-3.5 shrink-0" /> {{ readOnlyText }}
              </p>
            </div>
            <UTabs
              v-model="tab"
              :items="tabs"
              :content="false"
              color="neutral"
              size="sm"
              :ui="{ ...SEGMENTED_UI, root: 'w-full sm:w-fit' }"
            />
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
            <ExplorerStructure v-else :structure="structure" @table="openRef" />
          </div>
        </template>
      </div>
    </div>

    <USlideover
      v-model:open="treeOpen"
      side="left"
      :title="t('explorer.tables')"
      :ui="{ content: 'w-full max-w-xs', body: 'p-3' }"
    >
      <template #body>
        <ExplorerTree :tables="tables" :selected="objectKey" :loading="loadingTables" @select="open" />
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
    <template v-if="structure && dsId && !structure.read_only">
      <ExplorerRowForm
        v-model:open="formOpen"
        :source-id="dsId"
        :structure="structure"
        :row="editing"
        @saved="saved"
      />
      <ExplorerImportModal
        v-model:open="importOpen"
        :source-id="dsId"
        :structure="structure"
        @done="() => data?.refresh()"
      />
    </template>
  </AppPanel>
</template>
