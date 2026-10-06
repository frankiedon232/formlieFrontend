<!--
  Webhooks → Deliveries view (F13 M6): every delivery (DataView, table / cards) with webhook, result
  and event filters, a date range and search; a delivery opens its panel (`?delivery=`); ⋯: open,
  send again. The page's view switch sits at the start of the toolbar (slot).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import { WEBHOOK_EVENTS, type Webhook, type WebhookDelivery, type WebhookDeliveryDetail } from '#shared/types/integrations'
import { eventLabelKey } from '#shared/utils/integrations/webhooks'

const props = defineProps<{ webhooks: Webhook[] }>()
const emit = defineEmits<{ open: [id: string]; changed: [] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { relative, dateTime } = useFormat()

const list = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: Ref<WebhookDelivery[]> } }>('list')
defineExpose({ refresh: () => list.value?.refresh(), ids: () => (list.value?.state.rows.value ?? []).map(row => row.id) })

const columns = computed<DataColumn[]>(() => [
  { key: 'event', label: t('integrations.webhooks.col.event'), fixed: true },
  { key: 'status', label: t('integrations.webhooks.col.result') },
  { key: 'webhook', label: t('integrations.webhooks.col.webhook'), hideBelow: 'md' },
  { key: 'attempts', label: t('integrations.webhooks.col.tries'), sortable: true, hideBelow: 'lg' },
  { key: 'duration_ms', label: t('apiService.kpi.time'), sortable: true, hideBelow: 'lg' },
  { key: 'form', label: t('integrations.webhooks.col.form'), hideBelow: 'lg', hidden: true },
  { key: 'at', label: t('integrations.webhooks.col.at'), sortable: true },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'webhook', label: t('integrations.webhooks.col.webhook'), icon: 'i-lucide-webhook', options: props.webhooks.map(hook => ({ value: hook.id, label: hook.name })) },
  {
    key: 'status',
    label: t('integrations.webhooks.col.result'),
    icon: 'i-lucide-circle-check',
    options: (['delivered', 'retrying', 'failed'] as const).map(value => ({ value, label: t(`integrations.webhooks.delivery.${value}`), dot: value === 'delivered' ? 'bg-green-500' : value === 'retrying' ? 'bg-amber-500' : 'bg-red-500' })),
  },
  { key: 'event', label: t('integrations.webhooks.col.event'), icon: 'i-lucide-zap', options: [...WEBHOOK_EVENTS, 'ping' as const].map(value => ({ value, label: t(eventLabelKey(value)) })) },
])
const sortOptions = computed(() => [
  { label: t('integrations.webhooks.sort.newest'), value: '-at' },
  { label: t('integrations.webhooks.sort.oldest'), value: 'at' },
  { label: t('integrations.webhooks.sort.tries'), value: '-attempts' },
  { label: t('integrations.webhooks.sort.slowest'), value: '-duration_ms' },
])
const fetcher: DataFetcher<WebhookDelivery> = (params, signal) => api.list<WebhookDelivery>('/webhook-deliveries', params, { signal })

const busy = ref<string | null>(null)
async function resend(row: WebhookDelivery) {
  if (busy.value) return
  busy.value = row.id
  try {
    const { data } = await api.post<WebhookDeliveryDetail>(`/webhook-deliveries/${row.id}/resend`)
    toast.add({ title: data.status === 'delivered' ? t('integrations.webhooks.toast.resent') : t('integrations.webhooks.toast.resentFailed'), color: data.status === 'delivered' ? 'success' : 'warning', icon: data.status === 'delivered' ? 'i-lucide-circle-check' : 'i-lucide-triangle-alert' })
    await list.value?.refresh()
    emit('changed')
  } catch (error) {
    handle(error)
  } finally {
    busy.value = null
  }
}
const rowActions = (row: WebhookDelivery): DropdownMenuItem[][] => [
  [
    { label: t('apiService.actions.open'), icon: 'i-lucide-panel-right-open', onSelect: () => emit('open', row.id) },
    { label: row.status === 'retrying' ? t('integrations.webhooks.retryNow') : t('integrations.webhooks.sendAgain'), icon: 'i-lucide-send', onSelect: () => void resend(row) },
  ],
]
</script>

<template>
  <DataView
    id="webhook-deliveries"
    ref="list"
    :columns="columns"
    :fetcher="fetcher"
    :filters="filters"
    :sort-options="sortOptions"
    default-sort="-at"
    date-range
    :row-actions="rowActions"
    :busy="row => busy === row.id"
    :open-row="row => emit('open', row.id)"
    :search-placeholder="t('integrations.webhooks.searchDeliveries')"
    empty-icon="i-lucide-send"
    :empty-title="t('integrations.webhooks.noDeliveries')"
    :empty-description="t('integrations.webhooks.noDeliveriesDesc')"
  >
    <template #toolbar-start><slot name="switch" /></template>
    <template #event-cell="{ row }">
      <span class="flex min-w-0 items-center gap-2">
        <span class="max-w-56 truncate font-medium text-highlighted">{{ t(eventLabelKey(row.original.event)) }}</span>
        <UBadge v-if="row.original.test" :label="t('integrations.webhooks.test')" color="neutral" variant="soft" size="xs" class="rounded-md" />
      </span>
    </template>
    <template #status-cell="{ row }">
      <span class="flex items-center gap-1.5">
        <DataStatusBadge :status="row.original.status" :label="t(`integrations.webhooks.delivery.${row.original.status}`)" />
        <span class="font-mono text-xs text-muted tabular-nums">{{ row.original.status_code ?? '' }}</span>
      </span>
    </template>
    <template #webhook-cell="{ row }"><span class="block max-w-48 truncate">{{ row.original.webhook.name }}</span></template>
    <template #attempts-cell="{ row }"><span class="tabular-nums">{{ row.original.attempts }}</span></template>
    <template #duration_ms-cell="{ row }"><span class="text-muted tabular-nums">{{ row.original.duration_ms == null ? '–' : t('dataSources.ms', { n: row.original.duration_ms }) }}</span></template>
    <template #form-cell="{ row }"><span class="block max-w-48 truncate text-muted">{{ row.original.form?.name ?? '–' }}</span></template>
    <template #at-cell="{ row }">
      <UTooltip :text="dateTime(row.original.at)"><span class="whitespace-nowrap text-muted tabular-nums">{{ relative(row.original.at) }}</span></UTooltip>
    </template>
    <template #grid-card="{ row }">
      <IntegrationsWebhooksDeliveryCard :item="row" :actions="rowActions(row)" :busy="busy === row.id" />
    </template>
  </DataView>
</template>
