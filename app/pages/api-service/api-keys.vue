<!--
  API service → API keys (F13 M6; locked list format, rule 21): keys for Formalie's own management
  API (`{base}/v1/…`). Two chart cards (calls in 30 days; keys by status, the legend filters),
  DataView (table / cards) with status and scope filters; a key opens its panel (`?key=`); ⋯ /
  right-click: open, edit, revoke, delete (once revoked or expired). The key is shown once.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ApiServiceSettings } from '#shared/types/apiService'
import { API_KEY_SCOPES, type ApiKeyInsights, type ManagementKey, type ManagementKeyWithSecret } from '#shared/types/integrations'

definePageMeta({ breadcrumb: 'nav.apiKeys' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const confirm = useConfirm()
const toast = useToast()
const { handle } = useErrorHandler()
const { relative, dateTime, date, number } = useFormat()
useHead({ title: () => t('nav.apiKeys') })

const list = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: Ref<ManagementKey[]> } }>('list')
const panel = useTemplateRef<{ reload: () => void }>('panel')
const insights = ref<ApiKeyInsights | null>(null)
const base = ref('https://api.formalie.dev')
async function loadInsights() {
  try {
    insights.value = (await api.get<ApiKeyInsights>('/api-keys/insights', undefined, { background: !!insights.value })).data
  } catch {
    insights.value ??= null
  }
}
onMounted(async () => {
  void loadInsights()
  try {
    base.value = (await api.get<ApiServiceSettings>('/api-service/settings', undefined, { background: true })).data.base_url
  } catch {
    // the default address stays
  }
})
const refreshAll = () => Promise.all([list.value?.refresh(), loadInsights(), panel.value?.reload()])

const scopeLabel = (scope: string) => t(`integrations.keys.scope.${scope.replace(':', '_')}`)
const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('integrations.keys.col.name'), fixed: true, sortable: true },
  { key: 'status', label: t('integrations.keys.col.status') },
  { key: 'scopes', label: t('integrations.keys.col.scopes'), hideBelow: 'md' },
  { key: 'calls_30d', label: t('integrations.keys.col.calls'), sortable: true, hideBelow: 'lg' },
  { key: 'last_used_at', label: t('integrations.keys.col.lastUsed'), sortable: true, hideBelow: 'sm' },
  { key: 'expires_at', label: t('apiService.tokens.col.expires'), sortable: true, hideBelow: 'lg' },
  { key: 'created_at', label: t('apiService.col.created'), sortable: true, hideBelow: 'lg', hidden: true },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'status', label: t('integrations.keys.col.status'), icon: 'i-lucide-activity', options: (['active', 'expiring', 'expired', 'revoked'] as const).map(value => ({ value, label: t(`status.${value}`), dot: value === 'active' ? 'bg-green-500' : value === 'expiring' ? 'bg-amber-500' : value === 'expired' ? 'bg-violet-500' : 'bg-red-500' })) },
  { key: 'scope', label: t('integrations.keys.col.scopes'), icon: 'i-lucide-list-checks', options: API_KEY_SCOPES.map(value => ({ value, label: scopeLabel(value) })) },
])
const sortOptions = computed(() => [
  { label: t('apiService.sort.created'), value: '-created_at' },
  { label: t('integrations.webhooks.sort.name'), value: 'name' },
  { label: t('apiService.sort.calls'), value: '-calls_30d' },
  { label: t('integrations.keys.sort.lastUsed'), value: '-last_used_at' },
  { label: t('integrations.keys.sort.expires'), value: 'expires_at' },
])
const fetcher: DataFetcher<ManagementKey> = (params, signal) => api.list<ManagementKey>('/api-keys', params, { signal })
const statusFilter = computed(() => (typeof route.query.status === 'string' && !route.query.status.includes(',') ? route.query.status : null))
const pickStatus = (status: string) => void router.replace({ query: { ...route.query, status: statusFilter.value === status ? undefined : status, page: undefined } })

// The panel (`?key=`)
const openId = computed(() => (typeof route.query.key === 'string' ? route.query.key : null))
const panelOpen = computed({ get: () => !!openId.value, set: value => !value && router.replace({ query: { ...route.query, key: undefined } }) })
const ids = computed(() => (list.value?.state.rows.value ?? []).map(row => row.id))
const openRow = (row: Pick<ManagementKey, 'id'>) => void router.replace({ query: { ...route.query, key: row.id } })
const go = (id: string) => void router.replace({ query: { ...route.query, key: id } })

// New / edit / revoke / delete
const editOpen = ref(false)
const editing = ref<ManagementKey | null>(null)
function edit(key: ManagementKey | null) {
  editing.value = key
  editOpen.value = true
}
const secretOpen = ref(false)
const secret = ref<ManagementKeyWithSecret | null>(null)
const pendingOpen = ref<string | null>(null)
async function created(result: ManagementKeyWithSecret) {
  secret.value = result
  pendingOpen.value = result.key.id
  secretOpen.value = true
  await refreshAll()
}
watch(secretOpen, value => {
  if (value || !pendingOpen.value) return
  openRow({ id: pendingOpen.value })
  pendingOpen.value = null
})
async function saved() {
  toast.add({ title: t('integrations.keys.toast.saved'), color: 'success', icon: 'i-lucide-circle-check' })
  await refreshAll()
}
const usage = computed(() => `curl "${base.value}/v1/forms" \\\n  -H "Authorization: Bearer ${secret.value?.secret ?? 'formalie_key_…'}"`)
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
async function revoke(key: ManagementKey) {
  if (!(await confirm({ title: t('integrations.keys.revokeTitle'), description: t('integrations.keys.revokeDesc', { name: key.name }), confirmLabel: t('integrations.keys.revoke'), danger: true }))) return
  await act(key.id, () => api.post(`/api-keys/${key.id}/revoke`), t('integrations.keys.toast.revoked'))
}
async function remove(key: ManagementKey) {
  if (!(await confirm({ title: t('integrations.keys.deleteTitle'), description: t('integrations.keys.deleteDesc', { name: key.name }), confirmLabel: t('apiService.delete.confirm'), danger: true }))) return
  if ((await act(key.id, () => api.del(`/api-keys/${key.id}`), t('integrations.keys.toast.deleted'))) && openId.value === key.id) panelOpen.value = false
}
const rowActions = (row: ManagementKey): DropdownMenuItem[][] => {
  const done = row.status === 'revoked' || row.status === 'expired'
  return [
    [
      { label: t('apiService.actions.open'), icon: 'i-lucide-panel-right-open', onSelect: () => openRow(row) },
      ...(row.status !== 'revoked' ? [{ label: t('apiService.actions.edit'), icon: 'i-lucide-pencil', onSelect: () => edit(row) }] : []),
    ],
    done ? [{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove(row) }] : [{ label: t('integrations.keys.revoke'), icon: 'i-lucide-ban', color: 'error' as const, onSelect: () => void revoke(row) }],
  ]
}
defineShortcuts({ n: { usingInput: false, handler: () => edit(null) } })
</script>

<template>
  <AppPanel id="api-keys" :title="t('nav.apiKeys')" :subtitle="t('apiService.section.apiKeys')" subtitle-icon="i-lucide-key-round">
    <template #actions>
      <UButton :label="t('integrations.keys.newTitle')" icon="i-lucide-plus" color="neutral" @click="edit(null)">
        <template #trailing><UKbd value="N" size="sm" class="hidden sm:inline-flex" /></template>
      </UButton>
    </template>

    <IntegrationsKeysOverview :insights="insights" :status="statusFilter" @status="pickStatus" />

    <DataView
      id="api-keys"
      ref="list"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="-created_at"
      :row-actions="rowActions"
      :busy="row => busy === row.id"
      :open-row="openRow"
      :search-placeholder="t('integrations.keys.search')"
      empty-icon="i-lucide-key-round"
      :empty-title="t('integrations.keys.empty')"
      :empty-description="t('integrations.keys.emptyDesc')"
    >
      <template #name-cell="{ row }">
        <div class="flex min-w-0 flex-col">
          <span class="flex min-w-0 items-center gap-1.5">
            <UIcon v-if="row.original.status === 'expiring'" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" />
            <span class="max-w-64 truncate font-medium text-highlighted">{{ row.original.name }}</span>
          </span>
          <span class="font-mono text-xs text-muted" dir="ltr">{{ row.original.preview }}</span>
        </div>
      </template>
      <template #status-cell="{ row }"><DataStatusBadge :status="row.original.status" /></template>
      <template #scopes-cell="{ row }">
        <span class="flex max-w-72 gap-1 overflow-hidden"><code v-for="scope in row.original.scopes" :key="scope" class="shrink-0 rounded bg-elevated px-1.5 font-mono text-[11px] text-highlighted">{{ scope }}</code></span>
      </template>
      <template #calls_30d-cell="{ row }">
        <div class="flex items-center gap-2">
          <span class="w-10 tabular-nums">{{ number(row.original.calls_30d) }}</span>
          <ChartsSparkline :values="(row.original as ManagementKey).daily.map(day => day.count)" :width="64" :height="18" class="hidden sm:block" />
        </div>
      </template>
      <template #last_used_at-cell="{ row }">
        <UTooltip v-if="row.original.last_used_at" :text="dateTime(row.original.last_used_at)"><span class="whitespace-nowrap text-muted">{{ relative(row.original.last_used_at) }}</span></UTooltip>
        <span v-else class="text-muted">{{ t('integrations.keys.neverUsed') }}</span>
      </template>
      <template #expires_at-cell="{ row }"><span class="whitespace-nowrap" :class="row.original.status === 'expiring' ? 'font-medium text-warning' : 'text-muted'">{{ row.original.expires_at ? date(row.original.expires_at) : t('apiService.tokens.never') }}</span></template>
      <template #created_at-cell="{ row }"><span class="whitespace-nowrap text-muted">{{ relative(row.original.created_at) }}</span></template>
      <template #empty-actions>
        <UButton :label="t('integrations.keys.newTitle')" icon="i-lucide-plus" color="neutral" @click="edit(null)" />
      </template>
      <template #grid-card="{ row }">
        <IntegrationsKeysCard :item="row" :actions="rowActions(row)" :busy="busy === row.id" />
      </template>
    </DataView>

    <IntegrationsKeysDetail :id="openId" ref="panel" v-model:open="panelOpen" :ids="ids.length ? ids : openId ? [openId] : []" :busy="!!busy" :base="base" @go="go" @edit="edit" @revoke="revoke" @remove="remove" />
    <IntegrationsKeysEditModal v-model:open="editOpen" :api-key="editing" @saved="saved" @created="created" />
    <IntegrationsSecretModal v-model:open="secretOpen" :title="t('integrations.keys.secretTitle', { name: secret?.key.name ?? '' })" :secret="secret?.secret ?? null" :label="t('integrations.keys.secret')" :usage="usage" :hint="t('integrations.keys.secretHint')" />
  </AppPanel>
</template>
