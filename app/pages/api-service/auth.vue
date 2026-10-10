<!--
  API service → Tokens & headers (F13 M2; locked list format, rule 21). View switch Tokens | Headers
  (`?view=headers`). Tokens: two chart cards (calls with tokens; tokens by status, the legend
  filters), DataView (table / cards) with status, mode and kind filters; a token opens its panel
  (`?token=`); ⋯ / right-click: open, edit, rotate, revoke, delete (revoked or expired). New token
  shows its secrets once. Headers: the standard headers, the address key (rotate) and the endpoints
  with required headers.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ApiServiceSettings, ApiToken, ApiTokenInsights } from '#shared/types/apiService'

definePageMeta({ breadcrumb: 'nav.apiAuth' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const confirm = useConfirm()
const toast = useToast()
const { handle } = useErrorHandler()
const { relative, dateTime, number } = useFormat()
const format = useTokenFormat()
const { can } = useCan()
useHead({ title: () => t('nav.apiAuth') })

const view = computed({ get: () => (route.query.view === 'headers' ? 'headers' : 'tokens'), set: value => void router.replace({ query: { ...route.query, view: value === 'tokens' ? undefined : value } }) })
const views = computed(() => [
  { value: 'tokens', label: t('apiService.tokens.title'), icon: 'i-lucide-key-round' },
  { value: 'headers', label: t('apiService.headers.title'), icon: 'i-lucide-heading' },
])

const list = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: Ref<ApiToken[]> } }>('list')
const panel = useTemplateRef<{ reload: () => void }>('panel')
const insights = ref<ApiTokenInsights | null>(null)
const settings = ref<ApiServiceSettings | null>(null)
async function loadInsights() {
  try {
    insights.value = (await api.get<ApiTokenInsights>('/api-tokens/insights', undefined, { background: !!insights.value })).data
  } catch {
    insights.value ??= null
  }
}
onMounted(async () => {
  void loadInsights()
  try {
    settings.value = (await api.get<ApiServiceSettings>('/api-service/settings', undefined, { background: true })).data
  } catch {
    settings.value = null
  }
})
const base = computed(() => (settings.value ? `${settings.value.base_url}/${settings.value.api_key}` : ''))
const refreshAll = () => Promise.all([list.value?.refresh(), loadInsights(), panel.value?.reload()])

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('apiService.service.name'), sortable: true, fixed: true },
  { key: 'status', label: t('apiService.col.status'), hideBelow: 'sm' },
  { key: 'mode', label: t('apiService.tokens.col.mode'), hideBelow: 'md' },
  { key: 'kind', label: t('apiService.tokens.col.kind'), hideBelow: 'lg' },
  { key: 'scope', label: t('apiService.tokens.col.scope'), hideBelow: 'lg' },
  { key: 'calls_30d', label: t('apiService.col.calls'), sortable: true, hideBelow: 'md' },
  { key: 'last_used_at', label: t('apiService.tokens.col.lastUsed'), sortable: true },
  { key: 'expires_at', label: t('apiService.tokens.col.expires'), sortable: true, hideBelow: 'lg' },
  { key: 'created_at', label: t('apiService.col.created'), sortable: true, hideBelow: 'lg', hidden: true },
])
const STATUS_DOTS = { active: 'bg-green-500', expiring: 'bg-amber-500', expired: 'bg-(--ui-border-accented)', revoked: 'bg-red-500' } as const
const filters = computed<DataFilter[]>(() => [
  { key: 'status', label: t('apiService.col.status'), icon: 'i-lucide-circle-dot', options: (['active', 'expiring', 'expired', 'revoked'] as const).map(value => ({ value, label: t(`status.${value}`), dot: STATUS_DOTS[value] })) },
  { key: 'mode', label: t('apiService.tokens.col.mode'), icon: 'i-lucide-flask-conical', options: [{ value: 'live', label: t('apiService.tokens.mode.live') }, { value: 'test', label: t('apiService.tokens.mode.test') }] },
  { key: 'kind', label: t('apiService.tokens.col.kind'), icon: 'i-lucide-key-round', options: [{ value: 'static', label: t('apiService.tokens.kind.static') }, { value: 'client', label: t('apiService.tokens.kind.client') }, { value: 'webhook', label: t('apiService.tokens.kind.webhook') }] },
])
const sortOptions = computed(() => [
  { label: t('apiService.sort.created'), value: '-created_at' },
  { label: t('forms.sortName'), value: 'name' },
  { label: t('apiService.tokens.sort.used'), value: '-last_used_at' },
  { label: t('apiService.sort.calls'), value: '-calls_30d' },
  { label: t('apiService.tokens.sort.expires'), value: 'expires_at' },
])
const fetcher: DataFetcher<ApiToken> = (params, signal) => api.list<ApiToken>('/api-tokens', params, { signal })
const statusFilter = computed(() => (typeof route.query.status === 'string' && !route.query.status.includes(',') ? route.query.status : null))
const pickStatus = (status: string) => void router.replace({ query: { ...route.query, status: statusFilter.value === status ? undefined : status, page: undefined } })

// The panel (`?token=`)
const openId = computed(() => (typeof route.query.token === 'string' ? route.query.token : null))
const panelOpen = computed({ get: () => !!openId.value, set: value => !value && router.replace({ query: { ...route.query, token: undefined } }) })
const ids = computed(() => (list.value?.state.rows.value ?? []).map(row => row.id))
const openRow = (row: ApiToken) => void router.replace({ query: { ...route.query, token: row.id } })
const go = (id: string) => void router.replace({ query: { ...route.query, token: id } })

// New / edit / rotate / revoke / delete
const editOpen = ref(false)
const editing = ref<ApiToken | null>(null)
function edit(token: ApiToken | null) {
  editing.value = token
  editOpen.value = true
}
// `?new=1` (setup guide, an endpoint's checklist; `&endpoint=` presets what it may call)
const presetEndpoint = ref<string | null>(null)
watch(() => route.query.new, value => {
  if (!value) return
  presetEndpoint.value = typeof route.query.endpoint === 'string' ? route.query.endpoint : null
  if (can('api.tokens')) edit(null)
  void router.replace({ query: { ...route.query, new: undefined, endpoint: undefined } })
}, { immediate: true })
watch(editOpen, value => !value && (presetEndpoint.value = null))
async function saved(token: ApiToken) {
  if (editing.value) toast.add({ title: t('apiService.tokens.toast.saved', { name: token.name }), color: 'success', icon: 'i-lucide-circle-check' })
  await refreshAll()
}
const rotateOpen = ref(false)
const rotateTarget = ref<'token' | 'key'>('token')
const rotating = ref<ApiToken | null>(null)
function rotate(token: ApiToken | null) {
  if (!can(token ? 'api.tokens' : 'api.key')) return
  rotating.value = token
  rotateTarget.value = token ? 'token' : 'key'
  rotateOpen.value = true
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
async function revoke(token: ApiToken) {
  if (!(await confirm({ title: t('apiService.tokens.revokeTitle', { name: token.name }), description: t('apiService.tokens.revokeDesc'), confirmLabel: t('apiService.tokens.revoke'), danger: true }))) return
  await act(token.id, () => api.post(`/api-tokens/${token.id}/revoke`, {}), t('apiService.tokens.toast.revoked', { name: token.name }))
}
async function remove(token: ApiToken) {
  if (!(await confirm({ title: t('apiService.tokens.deleteTitle', { name: token.name }), description: t('apiService.tokens.deleteDesc'), confirmLabel: t('apiService.delete.confirm'), danger: true }))) return
  if ((await act(token.id, () => api.del(`/api-tokens/${token.id}`), t('apiService.tokens.toast.deleted', { name: token.name }))) && openId.value === token.id) panelOpen.value = false
}
// Changing tokens needs api.tokens (F22 R2 M4); without it the menu only opens the token
const rowActions = (row: ApiToken): DropdownMenuItem[][] => [
  [
    { label: t('apiService.actions.open'), icon: 'i-lucide-panel-right-open', onSelect: () => openRow(row) },
    ...(row.status !== 'revoked' && can('api.tokens') ? [{ label: t('apiService.actions.edit'), icon: 'i-lucide-pencil', onSelect: () => edit(row) }, { label: t('apiService.tokens.rotate'), icon: 'i-lucide-refresh-cw', onSelect: () => rotate(row) }] : []),
  ],
  !can('api.tokens')
    ? []
    : row.status === 'revoked' || row.status === 'expired'
      ? [{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove(row) }]
      : [{ label: t('apiService.tokens.revoke'), icon: 'i-lucide-ban', color: 'error' as const, onSelect: () => void revoke(row) }],
].filter(group => group.length)
defineShortcuts({ n: { usingInput: false, handler: () => can('api.tokens') && edit(null) } })
</script>

<template>
  <AppPanel id="api-auth" :title="t('nav.apiAuth')" :subtitle="t('apiService.section.auth')" subtitle-icon="i-lucide-key-round">
    <template #actions>
      <UButton v-if="can('api.tokens')" :label="t('apiService.tokens.newTitle')" icon="i-lucide-plus" color="neutral" @click="edit(null)">
        <template #trailing><UKbd value="N" size="sm" class="hidden sm:inline-flex" /></template>
      </UButton>
    </template>

    <template v-if="view === 'tokens'">
      <ApiTokensOverview :insights="insights" :status="statusFilter" @status="pickStatus" />
      <DataView
        id="api-tokens"
        ref="list"
        :columns="columns"
        :fetcher="fetcher"
        :filters="filters"
        :sort-options="sortOptions"
        default-sort="-created_at"
        :row-actions="rowActions"
        :busy="row => busy === row.id"
        :open-row="openRow"
        :search-placeholder="t('apiService.tokens.search')"
        empty-icon="i-lucide-key-round"
        :empty-title="t('apiService.tokens.empty')"
        :empty-description="t('apiService.tokens.emptyDesc')"
      >
        <template #toolbar-start>
          <UTabs v-model="view" :items="views" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" :aria-label="t('apiService.tokens.viewSwitch')" />
        </template>
        <template #name-cell="{ row }">
          <div class="flex min-w-0 flex-col">
            <span class="flex min-w-0 items-center gap-1.5">
              <UIcon v-if="format.flagged(row.original)" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('apiService.tokens.needsLook')" />
              <span class="truncate font-medium text-highlighted">{{ row.original.name }}</span>
            </span>
            <span class="truncate font-mono text-[11px] text-muted" dir="ltr">{{ row.original.preview }}</span>
          </div>
        </template>
        <template #status-cell="{ row }"><DataStatusBadge :status="row.original.status" /></template>
        <template #mode-cell="{ row }">
          <UBadge :label="t(`apiService.tokens.mode.${row.original.mode}`)" :icon="row.original.mode === 'test' ? 'i-lucide-flask-conical' : 'i-lucide-zap'" color="neutral" :variant="row.original.mode === 'test' ? 'soft' : 'outline'" size="sm" class="rounded-md" />
        </template>
        <template #kind-cell="{ row }"><span class="whitespace-nowrap">{{ format.kindLabel(row.original) }}</span></template>
        <template #scope-cell="{ row }"><span class="block max-w-56 truncate text-muted">{{ format.scopeText(row.original as ApiToken) }}</span></template>
        <template #calls_30d-cell="{ row }">
          <div class="flex items-center gap-2">
            <span class="w-12 tabular-nums">{{ number(row.original.calls_30d) }}</span>
            <ChartsSparkline :values="(row.original as ApiToken).daily.map(day => day.count)" :width="64" :height="18" class="hidden sm:block" />
          </div>
        </template>
        <template #last_used_at-cell="{ row }">
          <UTooltip v-if="row.original.last_used_at" :text="dateTime(row.original.last_used_at)"><span class="whitespace-nowrap text-muted">{{ relative(row.original.last_used_at) }}</span></UTooltip>
          <span v-else class="text-muted">{{ t('apiService.tokens.notUsed') }}</span>
        </template>
        <template #expires_at-cell="{ row }"><span class="whitespace-nowrap" :class="row.original.status === 'expiring' ? 'font-medium text-warning' : 'text-muted'">{{ format.expiresText(row.original) }}</span></template>
        <template #created_at-cell="{ row }"><span class="whitespace-nowrap text-muted">{{ relative(row.original.created_at) }}</span></template>
        <template #empty-actions>
          <UButton v-if="can('api.tokens')" :label="t('apiService.tokens.newTitle')" icon="i-lucide-plus" color="neutral" @click="edit(null)" />
        </template>
        <template #grid-card="{ row }">
          <ApiTokensCard :item="row" :actions="rowActions(row)" :busy="busy === row.id" />
        </template>
      </DataView>
    </template>
    <template v-else>
      <div class="flex shrink-0 items-center">
        <UTabs v-model="view" :items="views" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" :aria-label="t('apiService.tokens.viewSwitch')" />
      </div>
      <ApiHeadersView :settings="settings" @rotate-key="rotate(null)" />
    </template>

    <ApiTokensDetail :id="openId" ref="panel" v-model:open="panelOpen" :ids="ids.length ? ids : openId ? [openId] : []" :busy="!!busy" @go="go" @edit="edit" @rotate="rotate" @revoke="revoke" @remove="remove" />
    <ApiTokensEditModal v-model:open="editOpen" :token="editing" :base="base" :preset-endpoint="presetEndpoint" @saved="saved" />
    <ApiTokensRotateModal v-model:open="rotateOpen" :token="rotating" :target="rotateTarget" :base="base" @rotated="() => void refreshAll()" @key="value => (settings = value)" />
  </AppPanel>
</template>
