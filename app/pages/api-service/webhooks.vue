<!--
  API service → Webhooks (F13 M6; locked list format, rule 21). Two chart cards (deliveries in 30
  days; webhooks by status, the legend filters), then the view switch Webhooks | Deliveries
  (`?view=deliveries`). Webhooks: DataView (table / cards) with status and event filters; a webhook
  opens its panel (`?hook=`); ⋯ / right-click: open, edit, send a test, on / off, new secret,
  delete. Deliveries: every call made, a delivery opens its panel (`?delivery=`). Secrets are shown once.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import { WEBHOOK_EVENTS, type Webhook, type WebhookInsights, type WebhookWithSecret } from '#shared/types/integrations'
import { eventLabelKey } from '#shared/utils/integrations/webhooks'

definePageMeta({ breadcrumb: 'nav.webhooks' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const confirm = useConfirm()
const toast = useToast()
const { handle } = useErrorHandler()
const { relative, dateTime, number, percent } = useFormat()
useHead({ title: () => t('nav.webhooks') })

const view = computed({ get: () => (route.query.view === 'deliveries' ? 'deliveries' : 'webhooks'), set: value => void router.replace({ query: { ...route.query, view: value === 'webhooks' ? undefined : value, page: undefined } }) })
const views = computed(() => [
  { value: 'webhooks', label: t('nav.webhooks'), icon: 'i-lucide-webhook' },
  { value: 'deliveries', label: t('integrations.webhooks.deliveries'), icon: 'i-lucide-send' },
])

const list = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: Ref<Webhook[]> } }>('list')
const log = useTemplateRef<{ refresh: () => Promise<void>; ids: () => string[] }>('log')
const panel = useTemplateRef<{ reload: () => void }>('panel')
const insights = ref<WebhookInsights | null>(null)
const all = ref<Webhook[]>([])
async function loadInsights() {
  try {
    const [a, b] = await Promise.all([api.get<WebhookInsights>('/webhooks/insights', undefined, { background: !!insights.value }), api.list<Webhook>('/webhooks', { page_size: 100, sort: 'name' }, { background: true })])
    insights.value = a.data
    all.value = b.data
  } catch {
    insights.value ??= null
  }
}
onMounted(loadInsights)
const refreshAll = () => Promise.all([list.value?.refresh(), log.value?.refresh(), loadInsights(), panel.value?.reload()])

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('integrations.webhooks.col.name'), fixed: true, sortable: true },
  { key: 'status', label: t('integrations.webhooks.col.status') },
  { key: 'events', label: t('integrations.webhooks.col.events'), hideBelow: 'md' },
  { key: 'deliveries_30d', label: t('integrations.webhooks.col.deliveries'), sortable: true, hideBelow: 'lg' },
  { key: 'success_rate', label: t('integrations.webhooks.kpi.delivered'), sortable: true, hideBelow: 'md' },
  { key: 'last', label: t('integrations.webhooks.col.last'), hideBelow: 'lg' },
  { key: 'enabled', label: t('integrations.webhooks.enabled'), hideBelow: 'sm' },
  { key: 'created_at', label: t('apiService.col.created'), sortable: true, hideBelow: 'lg', hidden: true },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'status', label: t('integrations.webhooks.col.status'), icon: 'i-lucide-activity', options: (['active', 'failing', 'paused'] as const).map(value => ({ value, label: t(`integrations.webhooks.status.${value}`), dot: value === 'active' ? 'bg-green-500' : value === 'failing' ? 'bg-red-500' : 'bg-amber-500' })) },
  { key: 'event', label: t('integrations.webhooks.col.events'), icon: 'i-lucide-zap', options: WEBHOOK_EVENTS.map(value => ({ value, label: t(eventLabelKey(value)) })) },
])
const sortOptions = computed(() => [
  { label: t('apiService.sort.created'), value: '-created_at' },
  { label: t('integrations.webhooks.sort.name'), value: 'name' },
  { label: t('integrations.webhooks.sort.deliveries'), value: '-deliveries_30d' },
  { label: t('integrations.webhooks.sort.worst'), value: 'success_rate' },
])
const fetcher: DataFetcher<Webhook> = (params, signal) => api.list<Webhook>('/webhooks', params, { signal })
const statusFilter = computed(() => (typeof route.query.status === 'string' && !route.query.status.includes(',') ? route.query.status : null))
const pickStatus = (status: string) => void router.replace({ query: { ...route.query, view: undefined, status: statusFilter.value === status ? undefined : status, page: undefined } })

// Panels (`?hook=`, `?delivery=`; `?webhook=` is the Deliveries filter)
const openId = computed(() => (typeof route.query.hook === 'string' ? route.query.hook : null))
const panelOpen = computed({ get: () => !!openId.value, set: value => !value && router.replace({ query: { ...route.query, hook: undefined } }) })
const ids = computed(() => (list.value?.state.rows.value ?? []).map(row => row.id))
const openRow = (row: Pick<Webhook, 'id'>) => void router.replace({ query: { ...route.query, hook: row.id, delivery: undefined } })
const go = (id: string) => void router.replace({ query: { ...route.query, hook: id } })
const deliveryId = computed(() => (typeof route.query.delivery === 'string' ? route.query.delivery : null))
const deliveryOpen = computed({ get: () => !!deliveryId.value, set: value => !value && router.replace({ query: { ...route.query, delivery: undefined } }) })
const deliveryIds = ref<string[]>([])
function openDelivery(id: string) {
  deliveryIds.value = log.value?.ids() ?? []
  void router.replace({ query: { ...route.query, delivery: id, hook: undefined } })
}
const showAll = (webhook: Pick<Webhook, 'id'>) => void router.replace({ query: { view: 'deliveries', webhook: webhook.id } })

// New / edit / test / on-off / rotate / delete
const editOpen = ref(false)
const editing = ref<Webhook | null>(null)
function edit(webhook: Webhook | null) {
  editing.value = webhook
  editOpen.value = true
}
const secretOpen = ref(false)
const secret = ref<WebhookWithSecret | null>(null)
// The new webhook's panel opens once its secret has been seen (two overlays at once would close each other)
const pendingOpen = ref<string | null>(null)
function showSecret(result: WebhookWithSecret) {
  pendingOpen.value = result.webhook.id
  if (openId.value) panelOpen.value = false
  secret.value = result
  secretOpen.value = true
}
async function created(result: WebhookWithSecret) {
  showSecret(result)
  await refreshAll()
}
watch(secretOpen, value => {
  if (value || !pendingOpen.value) return
  openRow({ id: pendingOpen.value })
  pendingOpen.value = null
})
async function saved() {
  toast.add({ title: t('integrations.webhooks.toast.saved'), color: 'success', icon: 'i-lucide-circle-check' })
  await refreshAll()
}
const usage = computed(() => [`X-Formalie-Timestamp: <unix seconds>`, `X-Formalie-Signature: sha256=HMAC_SHA256(secret, "{timestamp}.{raw body}")`].join('\n'))
const busy = ref<string | null>(null)
async function act(id: string, work: () => Promise<unknown>, success?: string) {
  if (busy.value) return false
  busy.value = id
  try {
    await work()
    if (success) toast.add({ title: success, color: 'success', icon: 'i-lucide-circle-check' })
    await refreshAll()
    return true
  } catch (error) {
    handle(error)
    return false
  } finally {
    busy.value = null
  }
}
const toggle = (webhook: Webhook, on: boolean) => void act(webhook.id, () => api.patch(`/webhooks/${webhook.id}`, { enabled: on }), on ? t('integrations.webhooks.toast.on') : t('integrations.webhooks.toast.off'))
async function rotate(webhook: Webhook) {
  if (!(await confirm({ title: t('integrations.webhooks.rotateTitle'), description: t('integrations.webhooks.rotateDesc'), confirmLabel: t('integrations.webhooks.rotate') }))) return
  await act(webhook.id, async () => {
    showSecret((await api.post<WebhookWithSecret>(`/webhooks/${webhook.id}/rotate`)).data)
  }, t('integrations.webhooks.toast.rotated'))
}
async function remove(webhook: Webhook) {
  if (!(await confirm({ title: t('integrations.webhooks.deleteTitle'), description: t('integrations.webhooks.deleteDesc', { name: webhook.name }), confirmLabel: t('apiService.delete.confirm'), danger: true }))) return
  if ((await act(webhook.id, () => api.del(`/webhooks/${webhook.id}`), t('integrations.webhooks.toast.deleted'))) && openId.value === webhook.id) panelOpen.value = false
}
async function test(webhook: Webhook) {
  const { data } = await api.post<{ id: string; status: string }>(`/webhooks/${webhook.id}/test`)
  toast.add({ title: data.status === 'delivered' ? t('integrations.webhooks.testOk') : t('integrations.webhooks.testFailed'), color: data.status === 'delivered' ? 'success' : 'warning', icon: data.status === 'delivered' ? 'i-lucide-circle-check' : 'i-lucide-triangle-alert', actions: [{ label: t('integrations.webhooks.details'), color: 'neutral', variant: 'outline', onClick: () => openDelivery(data.id) }] })
}
const sendTest = (webhook: Webhook) => void act(webhook.id, () => test(webhook))
const rowActions = (row: Webhook): DropdownMenuItem[][] => [
  [
    { label: t('apiService.actions.open'), icon: 'i-lucide-panel-right-open', onSelect: () => openRow(row) },
    { label: t('apiService.actions.edit'), icon: 'i-lucide-pencil', onSelect: () => edit(row) },
    { label: t('integrations.webhooks.sendTest'), icon: 'i-lucide-send', onSelect: () => sendTest(row) },
    { label: row.enabled ? t('apiService.actions.turnOff') : t('apiService.actions.turnOn'), icon: row.enabled ? 'i-lucide-circle-pause' : 'i-lucide-circle-play', onSelect: () => toggle(row, !row.enabled) },
    { label: t('integrations.webhooks.rotate'), icon: 'i-lucide-refresh-cw', onSelect: () => void rotate(row) },
  ],
  [{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove(row) }],
]
defineShortcuts({ n: { usingInput: false, handler: () => edit(null) } })
</script>

<template>
  <AppPanel id="webhooks" :title="t('nav.webhooks')" :subtitle="t('apiService.section.webhooks')" subtitle-icon="i-lucide-webhook">
    <template #actions>
      <UButton :label="t('integrations.webhooks.newTitle')" icon="i-lucide-plus" color="neutral" @click="edit(null)">
        <template #trailing><UKbd value="N" size="sm" class="hidden sm:inline-flex" /></template>
      </UButton>
    </template>

    <IntegrationsWebhooksOverview :insights="insights" :status="view === 'webhooks' ? statusFilter : null" @status="pickStatus" />

    <DataView
      v-if="view === 'webhooks'"
      id="webhooks"
      ref="list"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="-created_at"
      :row-actions="rowActions"
      :busy="row => busy === row.id"
      :open-row="openRow"
      :search-placeholder="t('integrations.webhooks.search')"
      empty-icon="i-lucide-webhook"
      :empty-title="t('integrations.webhooks.empty')"
      :empty-description="t('integrations.webhooks.emptyDesc')"
    >
      <template #toolbar-start>
        <UTabs v-model="view" :items="views" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" :aria-label="t('integrations.webhooks.viewSwitch')" />
      </template>
      <template #name-cell="{ row }">
        <div class="flex min-w-0 flex-col">
          <span class="flex min-w-0 items-center gap-1.5">
            <UIcon v-if="row.original.status === 'failing'" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" />
            <span class="max-w-64 truncate font-medium text-highlighted">{{ row.original.name }}</span>
          </span>
          <span class="max-w-72 truncate font-mono text-xs text-muted" dir="ltr">{{ row.original.url }}</span>
        </div>
      </template>
      <template #status-cell="{ row }"><DataStatusBadge :status="row.original.status" :label="t(`integrations.webhooks.status.${row.original.status}`)" /></template>
      <template #events-cell="{ row }">
        <span class="block max-w-56 truncate text-muted">{{ (row.original as Webhook).events.map(item => t(eventLabelKey(item))).join(', ') }}</span>
      </template>
      <template #deliveries_30d-cell="{ row }">
        <div class="flex items-center gap-2">
          <span class="w-10 tabular-nums">{{ number(row.original.deliveries_30d) }}</span>
          <ChartsSparkline :values="(row.original as Webhook).daily.map(day => day.count)" :width="64" :height="18" class="hidden sm:block" />
        </div>
      </template>
      <template #success_rate-cell="{ row }">
        <div class="flex w-28 items-center gap-2">
          <UProgress :model-value="Math.round((row.original.success_rate ?? 0) * 100)" size="xs" color="neutral" class="flex-1" />
          <span class="w-10 text-end text-xs tabular-nums">{{ row.original.success_rate == null ? '–' : percent(row.original.success_rate, 0) }}</span>
        </div>
      </template>
      <template #last-cell="{ row }">
        <UTooltip v-if="row.original.last_delivery" :text="dateTime(row.original.last_delivery.at)">
          <span class="flex items-center gap-1.5 whitespace-nowrap text-muted">
            <UIcon :name="row.original.last_delivery.ok ? 'i-lucide-circle-check' : 'i-lucide-circle-x'" class="size-3.5" :class="row.original.last_delivery.ok ? 'text-success' : 'text-error'" />{{ relative(row.original.last_delivery.at) }}
          </span>
        </UTooltip>
        <span v-else class="text-muted">{{ t('integrations.webhooks.noDeliveries') }}</span>
      </template>
      <template #enabled-cell="{ row }">
        <USwitch :model-value="row.original.enabled" size="sm" :disabled="!!busy" :aria-label="t('integrations.webhooks.enabled')" @click.stop @update:model-value="value => toggle(row.original as Webhook, !!value)" />
      </template>
      <template #created_at-cell="{ row }"><span class="whitespace-nowrap text-muted">{{ relative(row.original.created_at) }}</span></template>
      <template #empty-actions>
        <UButton :label="t('integrations.webhooks.newTitle')" icon="i-lucide-plus" color="neutral" @click="edit(null)" />
      </template>
      <template #grid-card="{ row }">
        <IntegrationsWebhooksCard :item="row" :actions="rowActions(row)" :busy="busy === row.id" />
      </template>
    </DataView>
    <IntegrationsWebhooksDeliveries v-else ref="log" :webhooks="all" @open="openDelivery" @changed="loadInsights">
      <template #switch>
        <UTabs v-model="view" :items="views" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" :aria-label="t('integrations.webhooks.viewSwitch')" />
      </template>
    </IntegrationsWebhooksDeliveries>

    <IntegrationsWebhooksDetail :id="openId" ref="panel" v-model:open="panelOpen" :ids="ids.length ? ids : openId ? [openId] : []" :busy="!!busy" @go="go" @edit="edit" @toggle="toggle" @remove="remove" @rotate="rotate" @delivery="openDelivery" @all="showAll" />
    <IntegrationsWebhooksDeliveryDetail :id="deliveryId" v-model:open="deliveryOpen" :ids="deliveryIds.length ? deliveryIds : deliveryId ? [deliveryId] : []" @go="openDelivery" @webhook="id => openRow({ id })" @sent="id => { refreshAll(); openDelivery(id) }" />
    <IntegrationsWebhooksEditModal v-model:open="editOpen" :webhook="editing" @saved="saved" @created="created" />
    <IntegrationsSecretModal v-model:open="secretOpen" :title="t('integrations.webhooks.secretTitle', { name: secret?.webhook.name ?? '' })" :secret="secret?.secret ?? null" :label="t('integrations.webhooks.secret')" :usage="usage" :hint="t('integrations.webhooks.secretHint')" />
  </AppPanel>
</template>
