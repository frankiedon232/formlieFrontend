<!--
  Data sources → Query editor (F12 M4; the explorer's mode, owner 2026-10-05: the connection,
  tables and history in the menu column, the full page for the work). Tabs of statements, a SQL
  editor (CodeMirror 6) above the results, a line between them to drag. Ctrl / ⌘ + Enter runs the
  selection or the statement at the cursor; `:name` parameters get input boxes. Reading statements
  page through results; anything that changes rows or structure asks first (what it will do, how
  many rows) and follows the connection's access. Esc cancels a running statement. Ctrl / Cmd + S
  saves (yours: updated; otherwise a name and sharing), Shift + Alt + F formats. `?ds=` keeps the
  connection, `?saved=` opens a saved query.
-->
<script setup lang="ts">
import type { DataSourceRow } from '#shared/types/datasources'
import type { DatabaseTable } from '#shared/types/destinations'
import type { SavedQuery } from '#shared/types/query'
import { formatSql, parametersIn, splitStatements, tablesIn } from '#shared/utils/datasources/sql'

definePageMeta({ breadcrumb: 'nav.dataQuery' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const { handle, messageFor } = useErrorHandler()
// Running needs data.query, saving data.saved (also checked in each action, so the shortcuts follow)
const { can } = useCan()
useHead({ title: () => t('nav.dataQuery') })

// Connections and their tables (for the tree and completion)
const sources = ref<DataSourceRow[] | null>(null)
const dsId = computed(() => (typeof route.query.ds === 'string' ? route.query.ds : null))
const source = computed(() => sources.value?.find(item => item.id === dsId.value) ?? null)
const go = (ds: string) => void router.replace({ query: { ds } })
onMounted(async () => {
  try {
    sources.value = (await api.list<DataSourceRow>('/datasources', { page_size: 100, sort: 'name' })).data.filter(item => item.enabled)
    if (!dsId.value && sources.value.length) go((sources.value.find(item => item.status === 'connected') ?? sources.value[0])!.id)
  } catch (error) {
    sources.value = []
    handle(error)
  }
})
// Tables (names first) and their columns, loaded when a table is opened in the tree or named in the editor
const db = useDatabaseTables(dsId)
const { tables, error: tablesError } = db
const loadTables = () => db.load()
/** Completion: every `schema.table` and `table`; the columns of those loaded so far. */
const completion = computed(() => Object.fromEntries((tables.value ?? []).flatMap(table => {
  const columns = (db.columns.get(db.keyOf(table)) ?? []).map(column => column.name)
  return [[`${table.schema}.${table.name}`, columns], [table.name, columns]]
})))
const defaultSchema = computed(() => source.value?.access.schemas[0] ?? tables.value?.find(table => !table.formalie)?.schema)

// The menu column holds the connection, tables and history (the explorer's mode)
const takeover = useSidebarTakeover()
takeover.claim(() => t('nav.dataQuery'), 'i-lucide-square-terminal')
const sideOpen = ref(false)
watch(takeover.shown, shown => shown && (sideOpen.value = false))

// Tabs, the editor and running
const tabs = useQueryTabs(dsId)
const editor = useTemplateRef<{ runText: () => { text: string; from: number } | null; lineAt: (position: number) => number; insert: (text: string) => void; goToLine: (line: number) => void; focus: () => void }>('editor')
const runner = useQueryRunner(dsId, position => editor.value?.lineAt(position) ?? 1)
const state = computed(() => runner.stateOf(tabs.active.value.id))
const text = computed({ get: () => tabs.active.value.sql, set: value => tabs.update(tabs.active.value.id, value) })
// Columns of the tables the tab names (for completion), a moment after typing stops
watchDebounced(
  [text, tables],
  () => {
    for (const name of tablesIn(text.value)) {
      const lower = name.toLowerCase()
      const table = tables.value?.find(item => db.keyOf(item).toLowerCase() === lower || item.name.toLowerCase() === lower)
      if (table) void db.loadColumns(table)
    }
  },
  { debounce: 400, immediate: true },
)
const saved = useSavedQueries(dsId)
watch(dsId, () => {
  void runner.loadHistory()
  void saved.load()
}, { immediate: true })

// :name parameters of the tab, values kept per tab in memory
const paramValues = reactive(new Map<string, Record<string, string>>())
const paramNames = computed(() => parametersIn(text.value))
const valuesOf = (tabId: string) => {
  if (!paramValues.has(tabId)) paramValues.set(tabId, {})
  return paramValues.get(tabId)!
}

function run() {
  if (!can('data.query')) return
  const target = editor.value?.runText()
  if (!target || !dsId.value) return
  const names = parametersIn(target.text)
  const values = valuesOf(tabs.active.value.id)
  const missing = names.filter(name => !(name in values) || values[name] === '')
  if (missing.length) return void toast.add({ title: t('query.fillParams', { names: missing.map(name => `:${name}`).join(', ') }), color: 'warning', icon: 'i-lucide-variable' })
  // A saved query's run is counted on it when one of its saved statements runs
  const tab = tabs.active.value
  const savedId = tab.savedId && splitStatements(tab.savedSql ?? '').some(statement => statement.text === target.text.trim().replace(/;$/, '')) ? tab.savedId : undefined
  void runner.run(tab.id, target.text, target.from, Object.fromEntries(names.map(name => [name, values[name]!])), 1, false, savedId)
}
// Run all (Ctrl / Cmd + Shift + Enter): every statement of the tab, top to bottom, stopping at the first problem
function runAll() {
  const statements = splitStatements(text.value)
  if (!statements.length || !dsId.value || !can('data.query')) return
  const values = valuesOf(tabs.active.value.id)
  const names = [...new Set(statements.flatMap(statement => parametersIn(statement.text)))]
  const missing = names.filter(name => !(name in values) || values[name] === '')
  if (missing.length) return void toast.add({ title: t('query.fillParams', { names: missing.map(name => `:${name}`).join(', ') }), color: 'warning', icon: 'i-lucide-variable' })
  const paramsOf = (sql: string) => Object.fromEntries(parametersIn(sql).map(name => [name, values[name]!]))
  void runner.runAll(tabs.active.value.id, statements.map(statement => ({ text: statement.text, from: statement.from, params: paramsOf(statement.text) })))
}
const statementCount = computed(() => splitStatements(text.value).length)
const cancel = () => runner.cancel(tabs.active.value.id)
// Save (Ctrl / Cmd + S): updates your saved query, or asks for a name; Format (Shift + Alt + F)
const saveOpen = ref(false)
const saveBusy = ref(false)
const editing = ref<SavedQuery | null>(null)
async function save() {
  const tab = tabs.active.value
  if (!tab.sql.trim() || !can('data.saved')) return
  const linked = tab.savedId ? saved.list.value?.find(item => item.id === tab.savedId) : undefined
  if (linked?.mine) {
    saveBusy.value = true
    try {
      const data = await saved.update(linked.id, { sql: tab.sql })
      tabs.link(tab.id, data)
      toast.add({ title: t('query.saved.updated', { name: data.name }), color: 'success', icon: 'i-lucide-circle-check' })
    } catch (error) {
      handle(error)
    } finally {
      saveBusy.value = false
    }
    return
  }
  editing.value = null
  saveOpen.value = true
}
async function saveFromModal(values: { name: string; description: string | null; shared: boolean }) {
  saveBusy.value = true
  try {
    if (editing.value) {
      const data = await saved.update(editing.value.id, values)
      for (const tab of tabs.tabs.value.filter(item => item.savedId === data.id)) tabs.rename(tab.id, data.name)
      toast.add({ title: t('query.saved.updated', { name: data.name }), color: 'success', icon: 'i-lucide-circle-check' })
    } else {
      const data = await saved.create({ ...values, sql: tabs.active.value.sql })
      tabs.link(tabs.active.value.id, data)
      toast.add({ title: t('query.saved.created', { name: data.name }), color: 'success', icon: 'i-lucide-circle-check' })
    }
    saveOpen.value = false
  } catch (error) {
    handle(error)
  } finally {
    saveBusy.value = false
  }
}
function edit(item: SavedQuery) {
  editing.value = item
  saveOpen.value = true
}
async function removeSaved(item: SavedQuery) {
  if (await saved.remove(item)) tabs.unlink(item.id)
}
const openSaved = (item: SavedQuery) => {
  tabs.add(item.sql, item.name, { id: item.id, sql: item.sql })
  void nextTick(() => editor.value?.focus())
}
function format() {
  if (!text.value.trim()) return
  text.value = formatSql(text.value)
}

// ?saved= (from the Saved queries page): open it here, on its connection
watch(
  () => route.query.saved,
  async id => {
    if (typeof id !== 'string') return
    try {
      const item = await saved.get(id)
      if (item.datasource.id !== dsId.value) await router.replace({ query: { ds: item.datasource.id, saved: id } })
      await nextTick()
      openSaved(item)
      void router.replace({ query: { ds: item.datasource.id } })
    } catch (error) {
      handle(error)
    }
  },
  { immediate: true },
)

defineShortcuts({
  meta_s: { usingInput: true, handler: () => void save() },
  shift_alt_f: { usingInput: true, handler: format },
  meta_enter: { usingInput: true, handler: run },
  meta_shift_enter: { usingInput: true, handler: runAll },
  escape: { usingInput: true, handler: () => state.value.running && cancel() },
})

function open(sql: string, newTab: boolean) {
  if (newTab || tabs.active.value.sql.trim()) tabs.add(sql)
  else text.value = sql
  void nextTick(() => editor.value?.focus())
}
const insert = (value: string) => editor.value?.insert(value)

// The line between the editor and the results (dragged; remembered on this device)
const editorHeight = useLocalStorage('formalie:query-editor-height', 260)
let resizing: { start: number; height: number } | null = null
function resizeStart(event: PointerEvent) {
  resizing = { start: event.clientY, height: editorHeight.value }
  ;(event.target as HTMLElement).setPointerCapture(event.pointerId)
}
const resizeMove = (event: PointerEvent) => resizing && (editorHeight.value = Math.max(120, Math.min(900, resizing.height + event.clientY - resizing.start)))
const resizeKey = (event: KeyboardEvent) => {
  const step = event.key === 'ArrowDown' ? 24 : event.key === 'ArrowUp' ? -24 : 0
  if (!step) return
  event.preventDefault()
  editorHeight.value = Math.max(120, Math.min(900, editorHeight.value + step))
}

const navigator = computed(() => ({ sources: sources.value, sourceId: dsId.value, tables: tables.value, columns: db.columns, truncated: db.truncated.value, total: db.total.value, loading: db.loading.value, history: runner.history.value, engine: source.value?.engine ?? null, saved: saved.list.value, savedBusy: saved.busy.value }))
const navigatorEvents = {
  onSource: (id: string) => go(id),
  onInsert: insert,
  onOpen: open,
  onSelect: (table: DatabaseTable) => insert(`${table.schema}.${table.name}`),
  onExpand: (table: DatabaseTable) => void db.loadColumns(table),
  onSearch: db.search,
  onRemove: (id?: string) => void runner.removeHistory(id),
  onOpenSaved: openSaved,
  onEditSaved: edit,
  onShareSaved: (item: SavedQuery) => void saved.toggleShare(item),
  onDeleteSaved: (item: SavedQuery) => void removeSaved(item),
}
</script>

<template>
  <AppPanel id="data-query" :title="t('nav.dataQuery')" :subtitle="source ? `${source.name} · ${engineName(source.engine)}` : t('dataSources.section.query')" subtitle-icon="i-lucide-square-terminal">
    <template #actions>
      <UButton v-if="!takeover.shown.value" :label="t('query.side.title')" icon="i-lucide-list-tree" color="neutral" variant="outline" @click="sideOpen = true" />
      <UButton :label="t('query.format')" icon="i-lucide-align-left" color="neutral" variant="outline" class="hidden lg:inline-flex" :disabled="!text.trim()" @click="format" />
      <UButton v-if="can('data.saved')" :label="t('query.saved.saveButton')" icon="i-lucide-bookmark" color="neutral" variant="outline" class="hidden sm:inline-flex" :loading="saveBusy" :disabled="!dsId || !text.trim()" @click="save">
        <template #trailing><span class="hidden items-center gap-0.5 xl:inline-flex"><UKbd value="meta" size="sm" /><UKbd value="s" size="sm" /></span></template>
      </UButton>
      <UButton v-if="state.running" :label="t('query.cancel')" icon="i-lucide-square" color="neutral" variant="outline" @click="cancel">
        <template #trailing><UKbd value="Esc" size="sm" class="hidden sm:inline-flex" /></template>
      </UButton>
      <UButton v-if="statementCount > 1 && can('data.query')" :label="t('query.runAll.button')" icon="i-lucide-list-video" color="neutral" variant="outline" class="hidden md:inline-flex" :disabled="!dsId || state.running" @click="runAll">
        <template #trailing><span class="hidden items-center gap-0.5 xl:inline-flex"><UKbd value="meta" size="sm" /><UKbd value="shift" size="sm" /><UKbd value="enter" size="sm" /></span></template>
      </UButton>
      <UButton v-if="can('data.query')" :label="t('query.run')" icon="i-lucide-play" color="neutral" :loading="state.running" :disabled="!dsId || !text.trim()" @click="run">
        <template #trailing><span class="hidden items-center gap-0.5 sm:inline-flex"><UKbd value="meta" size="sm" /><UKbd value="enter" size="sm" /></span></template>
      </UButton>
    </template>

    <AppEmpty
      v-if="sources && !sources.length"
      icon="i-lucide-database"
      :title="t('explorer.noConnections')"
      :description="t('explorer.noConnectionsDesc')"
      :actions="can('data.create') ? [{ label: t('dataSources.add'), icon: 'i-lucide-plus', color: 'neutral', to: '/data-sources/connections/new' }] : []"
    />
    <AppEmpty
      v-else-if="tablesError"
      icon="i-lucide-plug-zap"
      :title="t('explorer.cantReach')"
      :description="messageFor(tablesError)"
      :actions="[
        { label: t('common.retry'), icon: 'i-lucide-rotate-cw', color: 'neutral', variant: 'outline', onClick: () => void loadTables() },
        { label: t('explorer.checkConnection'), icon: 'i-lucide-activity', color: 'neutral', to: { path: '/data-sources/connections', query: { connection: dsId } } },
      ]"
    />
    <div v-else class="flex h-[calc(100dvh-10.5rem)] min-h-[32rem] flex-col overflow-hidden rounded-lg border border-default">
      <QueryTabBar :tabs="tabs.tabs.value" :active="tabs.active.value.id" :running="id => runner.stateOf(id).running" :dirty="tabs.dirty" @select="tabs.select" @close="tabs.close" @add="tabs.add()" @rename="tabs.rename" />

      <!-- :name parameters -->
      <div v-if="paramNames.length" class="flex flex-wrap items-center gap-2 border-b border-default bg-elevated/30 px-3 py-1.5">
        <span class="flex items-center gap-1 text-xs text-muted"><UIcon name="i-lucide-variable" class="size-3.5" /> {{ t('query.params') }}</span>
        <UFieldGroup v-for="name in paramNames" :key="name" size="xs">
          <UBadge :label="`:${name}`" color="neutral" variant="outline" class="font-mono" />
          <UInput
            :model-value="valuesOf(tabs.active.value.id)[name] ?? ''"
            :placeholder="t('query.paramValue')"
            class="w-36"
            :aria-label="t('query.paramFor', { name })"
            @update:model-value="value => (valuesOf(tabs.active.value.id)[name] = String(value))"
          />
        </UFieldGroup>
      </div>

      <div class="shrink-0" :style="{ height: `${editorHeight}px` }">
        <ClientOnly>
          <QuerySqlEditor
            ref="editor"
            :key="`${dsId}:${tabs.active.value.id}`"
            v-model="text"
            :engine="source?.engine ?? 'postgresql'"
            :schema="completion"
            :default-schema="defaultSchema"
            :error-line="(state.batch ? state.batch.find(item => item.problem)?.problem?.line : state.problem?.line) ?? null"
            :placeholder-text="t('query.placeholder')"
            @run="run"
          />
          <template #fallback><USkeleton class="m-3 h-40" /></template>
        </ClientOnly>
      </div>

      <div
        role="separator"
        tabindex="0"
        aria-orientation="horizontal"
        :aria-label="t('query.resizeEditor')"
        :aria-valuenow="editorHeight"
        class="group relative h-2 shrink-0 cursor-row-resize touch-none border-y border-default bg-elevated/40 focus-visible:outline-none"
        @pointerdown="resizeStart"
        @pointermove="resizeMove"
        @pointerup="resizing = null"
        @pointercancel="resizing = null"
        @keydown="resizeKey"
      >
        <span class="absolute inset-x-0 top-1/2 mx-auto h-0.5 w-10 -translate-y-1/2 rounded-full bg-(--ui-border-accented) group-hover:bg-(--ui-border-inverted) group-focus-visible:bg-(--ui-border-inverted)" />
      </div>

      <QueryOutput :state="state" :source-id="dsId" @page="page => runner.page(tabs.active.value.id, page)" @line="line => editor?.goToLine(line)" @show="index => (state.active = index)" />
    </div>

    <Teleport v-if="takeover.shown.value" :to="`#${SIDEBAR_TAKEOVER_ID}`" defer>
      <QueryNavigator v-bind="{ ...navigator, ...navigatorEvents }" />
    </Teleport>
    <QuerySaveModal v-if="can('data.saved')" v-model:open="saveOpen" v-model:busy="saveBusy" :sql="text" :connection="source?.name ?? ''" :existing="editing" :suggested-name="tabs.active.value.title" @save="saveFromModal" />
    <USlideover v-model:open="sideOpen" side="left" :title="t('query.side.title')" :ui="{ content: 'w-full max-w-xs', body: 'flex p-0 sm:p-0' }">
      <template #body>
        <QueryNavigator v-bind="{ ...navigator, ...navigatorEvents }" />
      </template>
    </USlideover>
  </AppPanel>
</template>
