<!--
  API service → Access rules (F13 M3; locked list format, rule 21). View switch Rules | Rate limits
  (`?view=limits`). Rules: two chart cards (calls refused in 30 days; rules by kind, the legend
  filters), DataView (table / cards) with action, kind, where and on / off filters; a rule opens its
  panel (`?rule=`); ⋯ / right-click: open, edit, on / off, delete. Test a caller in the header.
  Block always wins; when allow rules apply, a caller must match one of them.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ApiAccessInsights, ApiAccessRule } from '#shared/types/apiService'

definePageMeta({ breadcrumb: 'nav.apiAccess' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const confirm = useConfirm()
const toast = useToast()
const { handle } = useErrorHandler()
const { relative, dateTime, number } = useFormat()
const format = useRuleFormat()
useHead({ title: () => t('nav.apiAccess') })

const view = computed({ get: () => (route.query.view === 'limits' ? 'limits' : 'rules'), set: value => void router.replace({ query: { ...route.query, view: value === 'rules' ? undefined : value } }) })
const views = computed(() => [
  { value: 'rules', label: t('apiService.access.rules'), icon: 'i-lucide-shield' },
  { value: 'limits', label: t('apiService.access.limits.title'), icon: 'i-lucide-gauge' },
])

const list = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: Ref<ApiAccessRule[]> } }>('list')
const panel = useTemplateRef<{ reload: () => void }>('panel')
const insights = ref<ApiAccessInsights | null>(null)
async function loadInsights() {
  try {
    insights.value = (await api.get<ApiAccessInsights>('/api-access-rules/insights', undefined, { background: !!insights.value })).data
  } catch {
    insights.value ??= null
  }
}
onMounted(loadInsights)
const refreshAll = () => Promise.all([list.value?.refresh(), loadInsights(), panel.value?.reload()])

const columns = computed<DataColumn[]>(() => [
  { key: 'values', label: t('apiService.access.col.values'), fixed: true },
  { key: 'action', label: t('apiService.access.col.action'), sortable: true },
  { key: 'kind', label: t('apiService.access.col.kind'), hideBelow: 'md' },
  { key: 'scope', label: t('apiService.access.col.scope'), hideBelow: 'md' },
  { key: 'enabled', label: t('apiService.access.col.state'), hideBelow: 'sm' },
  { key: 'hits_30d', label: t('apiService.access.col.hits'), sortable: true, hideBelow: 'lg' },
  { key: 'last_hit_at', label: t('apiService.access.col.lastHit'), sortable: true, hideBelow: 'lg' },
  { key: 'created_at', label: t('apiService.col.created'), sortable: true, hideBelow: 'lg', hidden: true },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'action', label: t('apiService.access.col.action'), icon: 'i-lucide-shield', options: [{ value: 'block', label: t('apiService.access.action.block'), dot: 'bg-red-500' }, { value: 'allow', label: t('apiService.access.action.allow'), dot: 'bg-green-500' }] },
  { key: 'kind', label: t('apiService.access.col.kind'), icon: 'i-lucide-network', options: (['ip', 'domain', 'country', 'region'] as const).map(value => ({ value, label: format.kindLabel(value) })) },
  { key: 'scope', label: t('apiService.access.col.scope'), icon: 'i-lucide-target', options: (['all', 'service', 'endpoint'] as const).map(value => ({ value, label: t(`apiService.access.scope.${value}`) })) },
  { key: 'state', label: t('apiService.access.col.state'), icon: 'i-lucide-toggle-right', options: [{ value: 'on', label: t('apiService.access.on') }, { value: 'off', label: t('apiService.access.off') }] },
])
const sortOptions = computed(() => [
  { label: t('apiService.sort.created'), value: '-created_at' },
  { label: t('apiService.access.sort.hits'), value: '-hits_30d' },
  { label: t('apiService.access.sort.lastHit'), value: '-last_hit_at' },
  { label: t('apiService.access.sort.blockFirst'), value: '-action' },
])
const fetcher: DataFetcher<ApiAccessRule> = (params, signal) => api.list<ApiAccessRule>('/api-access-rules', params, { signal })
const kindFilter = computed(() => (typeof route.query.kind === 'string' && !route.query.kind.includes(',') ? route.query.kind : null))
const pickKind = (kind: string) => void router.replace({ query: { ...route.query, kind: kindFilter.value === kind ? undefined : kind, page: undefined } })

// The panel (`?rule=`)
const openId = computed(() => (typeof route.query.rule === 'string' ? route.query.rule : null))
const panelOpen = computed({ get: () => !!openId.value, set: value => !value && router.replace({ query: { ...route.query, rule: undefined } }) })
const ids = computed(() => (list.value?.state.rows.value ?? []).map(row => row.id))
const openRow = (row: Pick<ApiAccessRule, 'id'>) => void router.replace({ query: { ...route.query, rule: row.id, view: undefined } })
const go = (id: string) => void router.replace({ query: { ...route.query, rule: id } })

// New / edit / on-off / delete / test
const editOpen = ref(false)
const editing = ref<ApiAccessRule | null>(null)
function edit(rule: ApiAccessRule | null) {
  editing.value = rule
  editOpen.value = true
}
async function saved(rule: ApiAccessRule) {
  toast.add({ title: editing.value ? t('apiService.access.toast.saved') : t('apiService.access.toast.created'), color: 'success', icon: 'i-lucide-circle-check' })
  await refreshAll()
  if (!editing.value) openRow(rule)
}
const busy = ref<string | null>(null)
async function act(id: string, work: () => Promise<unknown>, success: string) {
  if (busy.value) return false
  busy.value = id
  try {
    await work()
    toast.add({ title: success, color: 'success', icon: 'i-lucide-circle-check' })
    await refreshAll()
    return true
  } catch (error) {
    handle(error)
    return false
  } finally {
    busy.value = null
  }
}
const toggle = (rule: ApiAccessRule, on: boolean) => void act(rule.id, () => api.patch(`/api-access-rules/${rule.id}`, { enabled: on }), on ? t('apiService.access.toast.on') : t('apiService.access.toast.off'))
async function remove(rule: ApiAccessRule) {
  if (!(await confirm({ title: t('apiService.access.deleteTitle'), description: t('apiService.access.deleteDesc', { values: format.valuesText(rule) }), confirmLabel: t('apiService.delete.confirm'), danger: true }))) return
  if ((await act(rule.id, () => api.del(`/api-access-rules/${rule.id}`), t('apiService.access.toast.deleted'))) && openId.value === rule.id) panelOpen.value = false
}
const testOpen = ref(false)
function fromTest(id: string) {
  testOpen.value = false
  openRow({ id })
}
const rowActions = (row: ApiAccessRule): DropdownMenuItem[][] => [
  [
    { label: t('apiService.actions.open'), icon: 'i-lucide-panel-right-open', onSelect: () => openRow(row) },
    { label: t('apiService.actions.edit'), icon: 'i-lucide-pencil', onSelect: () => edit(row) },
    { label: row.enabled ? t('apiService.actions.turnOff') : t('apiService.actions.turnOn'), icon: row.enabled ? 'i-lucide-circle-pause' : 'i-lucide-circle-play', onSelect: () => toggle(row, !row.enabled) },
  ],
  [{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove(row) }],
]
defineShortcuts({ n: { usingInput: false, handler: () => edit(null) } })
</script>

<template>
  <AppPanel id="api-access" :title="t('nav.apiAccess')" :subtitle="t('apiService.section.access')" subtitle-icon="i-lucide-shield-check">
    <template #actions>
      <UButton :label="t('apiService.access.test.title')" icon="i-lucide-shield-question" color="neutral" variant="outline" class="hidden sm:inline-flex" @click="testOpen = true" />
      <UButton :label="t('apiService.access.newTitle')" icon="i-lucide-plus" color="neutral" @click="edit(null)">
        <template #trailing><UKbd value="N" size="sm" class="hidden sm:inline-flex" /></template>
      </UButton>
    </template>

    <template v-if="view === 'rules'">
      <ApiAccessOverview :insights="insights" :kind="kindFilter" @kind="pickKind" />
      <DataView
        id="api-access-rules"
        ref="list"
        :columns="columns"
        :fetcher="fetcher"
        :filters="filters"
        :sort-options="sortOptions"
        default-sort="-created_at"
        :row-actions="rowActions"
        :busy="row => busy === row.id"
        :open-row="openRow"
        :search-placeholder="t('apiService.access.search')"
        empty-icon="i-lucide-shield"
        :empty-title="t('apiService.access.empty')"
        :empty-description="t('apiService.access.emptyDesc')"
      >
        <template #toolbar-start>
          <UTabs v-model="view" :items="views" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" :aria-label="t('apiService.access.viewSwitch')" />
        </template>
        <template #values-cell="{ row }">
          <div class="flex min-w-0 items-center gap-2">
            <UIcon :name="format.kindIcon(row.original.kind)" class="size-4 shrink-0 text-muted" />
            <div class="flex min-w-0 flex-col">
              <span class="max-w-72 truncate text-sm font-medium text-highlighted" :class="row.original.kind === 'ip' || row.original.kind === 'domain' ? 'font-mono' : ''" dir="ltr">{{ format.valuesText(row.original as ApiAccessRule) }}</span>
              <span v-if="row.original.note" class="max-w-72 truncate text-xs text-muted">{{ row.original.note }}</span>
            </div>
          </div>
        </template>
        <template #action-cell="{ row }">
          <UBadge :label="t(`apiService.access.action.${row.original.action}`)" :icon="row.original.action === 'block' ? 'i-lucide-ban' : 'i-lucide-check'" :color="row.original.action === 'block' ? 'error' : 'success'" variant="subtle" size="sm" class="rounded-md" />
        </template>
        <template #kind-cell="{ row }"><span class="whitespace-nowrap">{{ format.kindLabel(row.original.kind) }}</span></template>
        <template #scope-cell="{ row }"><span class="block max-w-48 truncate text-muted">{{ format.scopeText(row.original.scope) }}</span></template>
        <template #enabled-cell="{ row }">
          <USwitch :model-value="row.original.enabled" size="sm" :disabled="!!busy" :aria-label="t('apiService.access.enabled')" @click.stop @update:model-value="value => toggle(row.original as ApiAccessRule, !!value)" />
        </template>
        <template #hits_30d-cell="{ row }">
          <div class="flex items-center gap-2">
            <span class="w-10 tabular-nums">{{ number(row.original.hits_30d) }}</span>
            <ChartsSparkline :values="(row.original as ApiAccessRule).daily.map(day => day.count)" :width="64" :height="18" class="hidden sm:block" />
          </div>
        </template>
        <template #last_hit_at-cell="{ row }">
          <UTooltip v-if="row.original.last_hit_at" :text="dateTime(row.original.last_hit_at)"><span class="whitespace-nowrap text-muted">{{ relative(row.original.last_hit_at) }}</span></UTooltip>
          <span v-else class="text-muted">{{ t('apiService.access.neverHit') }}</span>
        </template>
        <template #created_at-cell="{ row }"><span class="whitespace-nowrap text-muted">{{ relative(row.original.created_at) }}</span></template>
        <template #empty-actions>
          <UButton :label="t('apiService.access.newTitle')" icon="i-lucide-plus" color="neutral" @click="edit(null)" />
        </template>
        <template #grid-card="{ row }">
          <ApiAccessCard :item="row" :actions="rowActions(row)" :busy="busy === row.id" />
        </template>
      </DataView>
    </template>
    <template v-else>
      <div class="flex shrink-0 items-center">
        <UTabs v-model="view" :items="views" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" :aria-label="t('apiService.access.viewSwitch')" />
      </div>
      <ApiAccessLimitsView />
    </template>

    <ApiAccessDetail :id="openId" ref="panel" v-model:open="panelOpen" :ids="ids.length ? ids : openId ? [openId] : []" :busy="!!busy" @go="go" @edit="edit" @toggle="toggle" @remove="remove" />
    <ApiAccessEditModal v-model:open="editOpen" :rule="editing" @saved="saved" />
    <ApiAccessTestModal v-model:open="testOpen" @rule="fromTest" />
  </AppPanel>
</template>
