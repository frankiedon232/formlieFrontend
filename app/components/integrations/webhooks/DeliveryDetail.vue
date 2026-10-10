<!--
  One webhook delivery in a panel from the side (F13 M6, detail panel model): header with the event,
  webhook and result; Send again (or Retry now while retries run) and Open the webhook; fact tiles;
  then Tries · Request · Answer (chips). The body shows personal answers masked. Previous (K) · Next (J).
-->
<script setup lang="ts">
import type { WebhookDeliveryDetail } from '#shared/types/integrations'
import { eventLabelKey } from '#shared/utils/integrations/webhooks'

const props = defineProps<{ id: string | null; ids: string[] }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string]; webhook: [id: string]; sent: [id: string] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { relative, dateTime } = useFormat()
// Sending a delivery again needs api.webhooks (F22 R2 M4)
const { can } = useCan()

const delivery = ref<WebhookDeliveryDetail | null>(null)
const failed = ref(false)
async function load(id: string) {
  failed.value = false
  try {
    const { data } = await api.get<WebhookDeliveryDetail>(`/webhook-deliveries/${id}`)
    if (props.id === id) delivery.value = data
  } catch {
    failed.value = true
  }
}
watch(() => [props.id, open.value] as const, ([id, isOpen]) => id && isOpen && void load(id), { immediate: true })

const index = computed(() => (props.id ? props.ids.indexOf(props.id) : -1))
const prev = computed(() => (index.value > 0 ? props.ids[index.value - 1] : null))
const next = computed(() => (index.value >= 0 && index.value < props.ids.length - 1 ? props.ids[index.value + 1] : null))
defineShortcuts({
  j: { usingInput: false, handler: () => open.value && next.value && emit('go', next.value) },
  k: { usingInput: false, handler: () => open.value && prev.value && emit('go', prev.value) },
})

const tiles = computed(() => {
  const d = delivery.value
  if (!d) return []
  return [
    { key: 'code', icon: 'i-lucide-hash', label: t('integrations.webhooks.col.code'), value: d.status_code == null ? '–' : String(d.status_code) },
    { key: 'time', icon: 'i-lucide-timer', label: t('apiService.kpi.time'), value: d.duration_ms == null ? '–' : t('dataSources.ms', { n: d.duration_ms }) },
    { key: 'tries', icon: 'i-lucide-repeat', label: t('integrations.webhooks.col.tries'), value: String(d.attempts) },
    { key: 'at', icon: 'i-lucide-clock', label: t('integrations.webhooks.col.at'), value: dateTime(d.at) },
    { key: 'next', icon: 'i-lucide-calendar-clock', label: t('integrations.webhooks.nextTry'), value: d.next_retry_at ? relative(d.next_retry_at) : '–' },
    { key: 'form', icon: 'i-lucide-file-text', label: t('integrations.webhooks.col.form'), value: d.form?.name ?? '–' },
  ]
})
const tab = ref<'tries' | 'request' | 'answer'>('tries')
const chips = computed(() => [
  { key: 'tries' as const, label: t('integrations.webhooks.col.tries'), count: delivery.value?.attempts ?? 0 },
  { key: 'request' as const, label: t('integrations.webhooks.request'), count: null },
  { key: 'answer' as const, label: t('apiService.call.answer'), count: null },
])
const pretty = (text: string | null | undefined) => {
  if (!text) return ''
  try {
    return JSON.stringify(JSON.parse(text), null, 2)
  } catch {
    return text
  }
}
const headerText = (headers: Record<string, string>) => Object.entries(headers).map(([name, value]) => `${name}: ${value}`).join('\n')
const errorText = (error: string | null) => (!error ? null : error.startsWith('HTTP') ? error : t(`integrations.webhooks.error.${error}`))

const sending = ref(false)
async function sendAgain() {
  if (!delivery.value || sending.value || !can('api.webhooks')) return
  sending.value = true
  try {
    const { data } = await api.post<WebhookDeliveryDetail>(`/webhook-deliveries/${delivery.value.id}/resend`)
    toast.add({ title: data.status === 'delivered' ? t('integrations.webhooks.toast.resent') : t('integrations.webhooks.toast.resentFailed'), color: data.status === 'delivered' ? 'success' : 'warning', icon: data.status === 'delivered' ? 'i-lucide-circle-check' : 'i-lucide-triangle-alert' })
    emit('sent', data.id)
  } catch (error) {
    handle(error)
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="delivery ? t(eventLabelKey(delivery.event)) : t('integrations.webhooks.deliveries')"
    :ui="{ content: 'w-full sm:max-w-2xl', header: 'border-b-0 pb-2', body: 'flex flex-col gap-6 pb-40', footer: 'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4' }"
  >
    <template #header>
      <div v-if="!delivery" class="flex w-full items-center gap-3.5">
        <USkeleton class="size-14 rounded-2xl" />
        <div class="flex flex-1 flex-col gap-2"><USkeleton class="h-5 w-48" /><USkeleton class="h-4 w-32" /></div>
      </div>
      <div v-else class="flex w-full flex-col gap-4">
        <div class="flex items-start gap-3.5">
          <span class="flex size-14 shrink-0 items-center justify-center rounded-2xl" :class="delivery.status === 'delivered' ? 'bg-inverted text-inverted' : delivery.status === 'retrying' ? 'bg-warning/10 text-warning' : 'bg-error/10 text-error'">
            <UIcon :name="delivery.status === 'delivered' ? 'i-lucide-send' : delivery.status === 'retrying' ? 'i-lucide-refresh-cw' : 'i-lucide-send-horizontal'" class="size-6" />
          </span>
          <div class="flex min-w-0 flex-1 flex-col gap-1">
            <h2 class="truncate text-lg leading-tight font-semibold text-highlighted">{{ t(eventLabelKey(delivery.event)) }}</h2>
            <p class="truncate text-sm text-muted">{{ delivery.webhook.name }} · <span class="font-mono text-xs" dir="ltr">{{ delivery.webhook.url }}</span></p>
            <div class="mt-1 flex flex-wrap items-center gap-1.5">
              <DataStatusBadge :status="delivery.status" :label="t(`integrations.webhooks.delivery.${delivery.status}`)" />
              <UBadge v-if="delivery.test" :label="t('integrations.webhooks.test')" color="neutral" variant="soft" size="sm" class="rounded-md" />
              <code class="font-mono text-xs text-muted">{{ delivery.event }}</code>
            </div>
          </div>
          <UButton icon="i-lucide-x" color="neutral" variant="soft" size="sm" square class="shrink-0 rounded-full" :aria-label="t('common.close')" @click="open = false" />
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <UButton v-if="can('api.webhooks')" :label="delivery.status === 'retrying' ? t('integrations.webhooks.retryNow') : t('integrations.webhooks.sendAgain')" icon="i-lucide-send" color="neutral" size="sm" :loading="sending" @click="sendAgain" />
          <UButton :label="t('integrations.webhooks.openWebhook')" icon="i-lucide-webhook" color="neutral" variant="outline" size="sm" @click="emit('webhook', delivery.webhook.id)" />
        </div>
      </div>
    </template>

    <template #body>
      <AppEmpty v-if="failed && !delivery" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" />
      <div v-else-if="!delivery" class="flex flex-col gap-4"><div class="grid grid-cols-2 gap-2 sm:grid-cols-3"><USkeleton v-for="n in 6" :key="n" class="h-14 rounded-lg" /></div></div>
      <template v-else>
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3" :class="sending ? 'opacity-60' : ''">
          <div v-for="tile in tiles" :key="tile.key" class="flex min-w-0 items-center gap-2.5 rounded-lg border border-default p-2.5">
            <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="tile.icon" class="size-4 text-muted" /></span>
            <div class="flex min-w-0 flex-col">
              <span class="truncate text-[11px] text-muted">{{ tile.label }}</span>
              <span class="truncate text-sm font-semibold text-highlighted tabular-nums">{{ tile.value }}</span>
            </div>
          </div>
        </div>

        <section class="flex flex-col gap-3">
          <div class="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1" role="tablist">
            <UButton v-for="chip in chips" :key="chip.key" :label="chip.label" role="tab" :aria-selected="tab === chip.key" color="neutral" :variant="tab === chip.key ? 'solid' : 'outline'" size="sm" class="shrink-0 rounded-full" @click="tab = chip.key">
              <template v-if="chip.count !== null" #trailing><span class="text-xs tabular-nums opacity-70">{{ chip.count }}</span></template>
            </UButton>
          </div>
          <ol v-if="tab === 'tries'" class="flex flex-col gap-2">
            <li v-for="(item, i) in [...delivery.history].reverse()" :key="item.at + i" class="flex min-w-0 items-center gap-3 rounded-lg border border-default px-3 py-2">
              <UIcon :name="item.error ? 'i-lucide-circle-x' : 'i-lucide-circle-check'" class="size-4 shrink-0" :class="item.error ? 'text-error' : 'text-success'" />
              <div class="flex min-w-0 flex-1 flex-col">
                <span class="text-sm text-highlighted">{{ t('integrations.webhooks.tryN', { n: delivery.history.length - i }) }}<span v-if="errorText(item.error)" class="text-muted"> · {{ errorText(item.error) }}</span></span>
                <span class="text-xs text-muted">{{ dateTime(item.at) }}</span>
              </div>
              <span class="font-mono text-xs text-muted tabular-nums">{{ item.status_code ?? '–' }} · {{ t('dataSources.ms', { n: item.duration_ms }) }}</span>
            </li>
            <li v-if="delivery.next_retry_at" class="flex items-center gap-3 rounded-lg border border-dashed border-default px-3 py-2 text-sm text-muted">
              <UIcon name="i-lucide-calendar-clock" class="size-4 shrink-0" />{{ t('integrations.webhooks.nextTryAt', { when: dateTime(delivery.next_retry_at) }) }}
            </li>
          </ol>
          <div v-else-if="tab === 'request'" class="flex flex-col gap-2">
            <pre class="overflow-x-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-default" dir="ltr">POST {{ delivery.webhook.url }}
{{ headerText(delivery.request.headers) }}</pre>
            <pre class="max-h-[28rem] overflow-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-default" dir="ltr">{{ pretty(delivery.request.body) }}</pre>
            <p class="text-xs text-muted">{{ t('integrations.webhooks.masked') }}</p>
          </div>
          <div v-else class="flex flex-col gap-2">
            <AppEmpty v-if="!delivery.response" size="sm" icon="i-lucide-unplug" :title="t('integrations.webhooks.noAnswer')" :description="errorText(delivery.history[delivery.history.length - 1]?.error ?? null) ?? undefined" />
            <template v-else>
              <pre v-if="Object.keys(delivery.response.headers).length" class="overflow-x-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-default" dir="ltr">{{ headerText(delivery.response.headers) }}</pre>
              <pre class="max-h-[28rem] overflow-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-default" dir="ltr">{{ pretty(delivery.response.body) || t('integrations.webhooks.emptyBody') }}</pre>
            </template>
          </div>
        </section>
      </template>
    </template>

    <template #footer>
      <nav class="pointer-events-auto flex items-center gap-1 rounded-full border border-default bg-default/95 p-1 shadow-lg backdrop-blur" :aria-label="t('apiService.navigate')">
        <UButton :label="t('responses.detail.prevShort')" icon="i-lucide-arrow-up" color="neutral" variant="ghost" size="sm" class="rounded-full" :disabled="!prev" @click="prev && emit('go', prev)">
          <template #trailing><UKbd value="K" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
        <span v-if="index >= 0" class="px-2 text-xs text-muted tabular-nums">{{ t('responses.detail.position', { n: index + 1, total: ids.length }) }}</span>
        <UButton :label="t('responses.detail.nextShort')" icon="i-lucide-arrow-down" color="neutral" variant="solid" size="sm" class="rounded-full" :disabled="!next" @click="next && emit('go', next)">
          <template #trailing><UKbd value="J" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
      </nav>
    </template>
  </USlideover>
</template>
