<!--
  Every response of the form with its delivery (F12 M2): sent, pending, held while paused, failed
  (with the reason, attempts and next retry; Retry), not sent (before the form stored here; use
  Send earlier responses). Filter chips in a sliding row; 25 at a time with Show more. A response
  number opens the response.
-->
<script setup lang="ts">
import type { Delivery, DeliveryStatus } from '#shared/types/destinations'

const props = defineProps<{ destinationId: string; formId: string; refreshKey: number }>()
const emit = defineEmits<{ retried: [] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const toast = useToast()
const { relative, dateTime, number } = useFormat()

const FILTERS: ('all' | DeliveryStatus)[] = ['all', 'failed', 'pending', 'held', 'sent', 'not_sent']
const filter = ref<'all' | DeliveryStatus>('all')
const rows = ref<Delivery[]>([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const failed = ref(false)
async function load(reset = true) {
  loading.value = true
  failed.value = false
  if (reset) page.value = 1
  try {
    const query: Record<string, unknown> = { page: page.value, page_size: 25 }
    if (filter.value !== 'all') query['filter[status]'] = filter.value
    const result = await api.list<Delivery>(`/destinations/${props.destinationId}/deliveries`, query, { background: !reset })
    rows.value = reset ? result.data : [...rows.value, ...result.data]
    total.value = result.meta.total
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  } finally {
    loading.value = false
  }
}
watch(() => [props.destinationId, filter.value, props.refreshKey], () => void load(), { immediate: true })
const more = () => {
  page.value++
  void load(false)
}

const retrying = ref<string | null>(null)
async function retry(delivery: Delivery) {
  retrying.value = delivery.response_id
  try {
    await api.post(`/destinations/${props.destinationId}/retry`, { response_ids: [delivery.response_id] })
    toast.add({ title: t('destinations.toast.retried', { n: 1 }, 1), color: 'success', icon: 'i-lucide-rotate-cw' })
    emit('retried')
    await load()
  } catch (error) {
    handle(error)
  } finally {
    retrying.value = null
  }
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <AppChipScroller :label="t('destinations.deliveries.filter')">
      <button
        v-for="item in FILTERS"
        :key="item"
        type="button"
        data-chip
        :aria-pressed="filter === item"
        class="inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-(--ui-border-inverted)"
        :class="filter === item ? 'bg-default text-highlighted shadow-xs ring-1 ring-(--ui-border)' : 'text-muted hover:text-highlighted'"
        @click="filter = item"
      >
        {{ t(`destinations.delivery.${item}`) }}
      </button>
    </AppChipScroller>

    <div v-if="loading && !rows.length" class="flex flex-col gap-2"><USkeleton v-for="n in 5" :key="n" class="h-12 rounded-lg" /></div>
    <AppEmpty v-else-if="failed && !rows.length" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => load() }]" variant="naked" />
    <AppEmpty v-else-if="!rows.length" size="sm" variant="outline" icon="i-lucide-send" :title="t('destinations.deliveries.empty')" />
    <ul v-else class="divide-y divide-default rounded-lg border border-default transition-opacity" :class="loading ? 'opacity-60' : ''">
      <li v-for="delivery in rows" :key="delivery.response_id" class="flex flex-col gap-1 px-3 py-2">
        <div class="flex items-center gap-2.5 text-sm">
          <NuxtLink :to="{ path: `/forms/${formId}/responses`, query: { response: delivery.response_id } }" class="font-mono text-xs text-highlighted hover:underline">#{{ delivery.number }}</NuxtLink>
          <span class="min-w-0 flex-1 truncate text-default">{{ delivery.respondent || `#${delivery.number}` }}</span>
          <UTooltip :text="dateTime(delivery.submitted_at)"><span class="hidden text-xs text-muted sm:inline">{{ relative(delivery.submitted_at) }}</span></UTooltip>
          <DataStatusBadge :status="delivery.status" :label="t(`destinations.delivery.${delivery.status}`)" />
          <UButton v-if="delivery.status === 'failed'" icon="i-lucide-rotate-cw" color="neutral" variant="ghost" size="xs" :loading="retrying === delivery.response_id" :aria-label="t('destinations.deliveries.retryOne', { n: delivery.number })" @click="retry(delivery)" />
        </div>
        <p v-if="delivery.status === 'failed'" class="ps-0.5 text-xs text-muted">
          <span class="text-error">{{ delivery.error_code ? t(`errors.${delivery.error_code}`) : '' }}</span>
          · {{ t('destinations.deliveries.attempts', { n: delivery.attempts }, delivery.attempts) }}
          <template v-if="delivery.next_retry_at"> · {{ t('destinations.deliveries.nextRetry', { when: relative(delivery.next_retry_at) }) }}</template>
        </p>
      </li>
    </ul>
    <div v-if="rows.length < total" class="flex justify-center">
      <UButton :label="t('destinations.deliveries.more', { shown: number(rows.length), total: number(total) })" color="neutral" variant="outline" size="sm" :loading="loading" @click="more" />
    </div>
  </div>
</template>
