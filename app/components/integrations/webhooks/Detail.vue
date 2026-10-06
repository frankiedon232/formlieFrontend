<!--
  A webhook in a panel from the side (F13 M6, detail panel model): header with its name, address,
  status and ⋯ (new secret, delete); a one-click bar (On / off, Send a test, Edit); a note when it
  paused itself; fact tiles; then Deliveries · Events and forms · Checking the signature (chips in a
  sliding row). Previous (K) · position · Next (J). Esc closes.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { Webhook, WebhookDelivery, WebhookDeliveryDetail } from '#shared/types/integrations'
import { eventLabelKey, WEBHOOK_AUTO_PAUSE } from '#shared/utils/integrations/webhooks'

const props = defineProps<{ id: string | null; ids: string[]; busy: boolean }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string]; edit: [webhook: Webhook]; toggle: [webhook: Webhook, on: boolean]; remove: [webhook: Webhook]; rotate: [webhook: Webhook]; delivery: [id: string]; all: [webhook: Webhook] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { number, percent, relative, date } = useFormat()

const webhook = ref<Webhook | null>(null)
const deliveries = ref<WebhookDelivery[] | null>(null)
const failed = ref(false)
async function load(id: string) {
  failed.value = false
  try {
    const [one, list] = await Promise.all([api.get<Webhook>(`/webhooks/${id}`), api.list<WebhookDelivery>('/webhook-deliveries', { 'filter[webhook]': id, page_size: 8 })])
    if (props.id !== id) return
    webhook.value = one.data
    deliveries.value = list.data
  } catch {
    failed.value = true
  }
}
watch(() => [props.id, open.value] as const, ([id, isOpen]) => {
  if (!id || !isOpen) return
  test.value = null
  void load(id)
}, { immediate: true })
defineExpose({ reload: () => props.id && load(props.id) })

const index = computed(() => (props.id ? props.ids.indexOf(props.id) : -1))
const prev = computed(() => (index.value > 0 ? props.ids[index.value - 1] : null))
const next = computed(() => (index.value >= 0 && index.value < props.ids.length - 1 ? props.ids[index.value + 1] : null))
defineShortcuts({
  j: { usingInput: false, handler: () => open.value && next.value && emit('go', next.value) },
  k: { usingInput: false, handler: () => open.value && prev.value && emit('go', prev.value) },
})

const tiles = computed(() => {
  const w = webhook.value
  if (!w) return []
  return [
    { key: 'deliveries', icon: 'i-lucide-send', label: t('integrations.webhooks.col.deliveries'), value: number(w.deliveries_30d) },
    { key: 'rate', icon: 'i-lucide-circle-check', label: t('integrations.webhooks.kpi.delivered'), value: w.success_rate == null ? '–' : percent(w.success_rate, 1) },
    { key: 'time', icon: 'i-lucide-timer', label: t('apiService.kpi.time'), value: w.avg_ms == null ? '–' : t('dataSources.ms', { n: w.avg_ms }) },
    { key: 'last', icon: 'i-lucide-clock', label: t('integrations.webhooks.col.last'), value: w.last_delivery ? relative(w.last_delivery.at) : t('integrations.webhooks.noDeliveries') },
    { key: 'secret', icon: 'i-lucide-key-round', label: t('integrations.webhooks.secret'), value: w.secret_preview },
    { key: 'by', icon: 'i-lucide-user-round', label: t('apiService.createdBy'), value: `${w.created_by.name} · ${date(w.created_at)}` },
  ]
})
const tab = ref<'deliveries' | 'events' | 'verify'>('deliveries')
const chips = computed(() => [
  { key: 'deliveries' as const, label: t('integrations.webhooks.col.deliveries'), count: webhook.value?.deliveries_30d ?? 0 },
  { key: 'events' as const, label: t('integrations.webhooks.eventsAndForms'), count: webhook.value?.events.length ?? 0 },
  { key: 'verify' as const, label: t('integrations.webhooks.verify.title'), count: null },
])
const menu = computed<DropdownMenuItem[][]>(() => {
  const w = webhook.value
  if (!w) return []
  return [
    [{ label: t('integrations.webhooks.rotate'), icon: 'i-lucide-refresh-cw', onSelect: () => emit('rotate', w) }],
    [{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => emit('remove', w) }],
  ]
})

// Send a test: a "ping" now, the receiver's answer shown here
const test = ref<WebhookDeliveryDetail | null>(null)
const testing = ref(false)
async function sendTest() {
  if (!webhook.value || testing.value) return
  testing.value = true
  try {
    test.value = (await api.post<WebhookDeliveryDetail>(`/webhooks/${webhook.value.id}/test`)).data
    tab.value = 'deliveries'
    if (props.id) void load(props.id)
  } catch (error) {
    handle(error)
  } finally {
    testing.value = false
  }
}
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="webhook?.name ?? t('nav.webhooks')"
    :ui="{ content: 'w-full sm:max-w-2xl', header: 'border-b-0 pb-2', body: 'flex flex-col gap-6 pb-40', footer: 'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4' }"
  >
    <template #header>
      <div v-if="!webhook" class="flex w-full items-center gap-3.5">
        <USkeleton class="size-14 rounded-2xl" />
        <div class="flex flex-1 flex-col gap-2"><USkeleton class="h-5 w-48" /><USkeleton class="h-4 w-32" /></div>
      </div>
      <div v-else class="flex w-full flex-col gap-4">
        <div class="flex items-start gap-3.5">
          <span class="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-inverted text-inverted"><UIcon name="i-lucide-webhook" class="size-6" /></span>
          <div class="flex min-w-0 flex-1 flex-col gap-1">
            <h2 class="truncate text-lg leading-tight font-semibold text-highlighted">{{ webhook.name }}</h2>
            <p class="truncate font-mono text-xs text-muted" dir="ltr">{{ webhook.url }}</p>
            <div class="mt-1 flex flex-wrap items-center gap-1.5">
              <DataStatusBadge :status="webhook.status" :label="t(`integrations.webhooks.status.${webhook.status}`)" />
              <UBadge v-for="event in webhook.events" :key="event" :label="t(eventLabelKey(event))" color="neutral" variant="outline" size="sm" class="rounded-md" />
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-1">
            <UDropdownMenu :items="menu" :content="{ align: 'end' }">
              <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="sm" square :aria-label="t('dataView.actions')" />
            </UDropdownMenu>
            <UButton icon="i-lucide-x" color="neutral" variant="soft" size="sm" square class="rounded-full" :aria-label="t('common.close')" @click="open = false" />
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <USwitch :model-value="webhook.enabled" :label="t('integrations.webhooks.enabled')" :disabled="busy" @update:model-value="value => emit('toggle', webhook!, !!value)" />
          <span class="mx-1 h-5 w-px bg-(--ui-border)" aria-hidden="true" />
          <UButton :label="t('integrations.webhooks.sendTest')" icon="i-lucide-send" color="neutral" size="sm" :loading="testing" @click="sendTest" />
          <UButton :label="t('apiService.actions.edit')" icon="i-lucide-pencil" color="neutral" variant="outline" size="sm" @click="emit('edit', webhook)" />
        </div>
      </div>
    </template>

    <template #body>
      <AppEmpty v-if="failed && !webhook" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" />
      <div v-else-if="!webhook" class="flex flex-col gap-4"><div class="grid grid-cols-2 gap-2 sm:grid-cols-3"><USkeleton v-for="n in 6" :key="n" class="h-14 rounded-lg" /></div></div>
      <template v-else>
        <UAlert v-if="webhook.paused_reason === 'failures'" icon="i-lucide-octagon-pause" color="error" variant="subtle" :title="t('integrations.webhooks.autoPaused', { n: WEBHOOK_AUTO_PAUSE })" :description="t('integrations.webhooks.autoPausedDesc')" />
        <UAlert v-else-if="webhook.status === 'failing'" icon="i-lucide-triangle-alert" color="warning" variant="subtle" :title="t('integrations.webhooks.failingTitle', { n: webhook.consecutive_failures }, webhook.consecutive_failures)" :description="t('integrations.webhooks.failingDesc')" />

        <div class="grid grid-cols-2 gap-2 transition-opacity sm:grid-cols-3" :class="busy ? 'opacity-60' : ''">
          <div v-for="tile in tiles" :key="tile.key" class="flex min-w-0 items-center gap-2.5 rounded-lg border border-default p-2.5">
            <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="tile.icon" class="size-4 text-muted" /></span>
            <div class="flex min-w-0 flex-col">
              <span class="truncate text-[11px] text-muted">{{ tile.label }}</span>
              <span class="truncate text-sm font-semibold text-highlighted tabular-nums" :class="tile.key === 'secret' ? 'font-mono text-xs' : ''">{{ tile.value }}</span>
            </div>
          </div>
        </div>

        <IntegrationsWebhooksTestResult v-if="test" :result="test" @open="emit('delivery', test.id)" />

        <section class="flex flex-col gap-3">
          <div class="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1" role="tablist">
            <UButton
              v-for="chip in chips"
              :key="chip.key"
              :label="chip.label"
              role="tab"
              :aria-selected="tab === chip.key"
              color="neutral"
              :variant="tab === chip.key ? 'solid' : 'outline'"
              size="sm"
              class="shrink-0 rounded-full"
              @click="tab = chip.key"
            >
              <template v-if="chip.count !== null" #trailing><span class="text-xs tabular-nums opacity-70">{{ chip.count }}</span></template>
            </UButton>
          </div>
          <IntegrationsWebhooksRecent v-if="tab === 'deliveries'" :deliveries="deliveries" @open="id => emit('delivery', id)" @all="emit('all', webhook)" />
          <div v-else-if="tab === 'events'" class="grid gap-2 sm:grid-cols-2">
            <div v-for="event in webhook.events" :key="event" class="flex min-w-0 flex-col gap-0.5 rounded-lg border border-default px-3 py-2">
              <span class="text-sm font-medium text-highlighted">{{ t(eventLabelKey(event)) }}</span>
              <code class="font-mono text-xs text-muted">{{ event }}</code>
            </div>
            <div class="flex min-w-0 flex-col gap-1 rounded-lg border border-default px-3 py-2 sm:col-span-2">
              <span class="text-xs text-muted">{{ t('integrations.webhooks.col.forms') }}</span>
              <span v-if="!webhook.forms.length" class="text-sm text-highlighted">{{ t('integrations.webhooks.allForms') }}</span>
              <div v-else class="flex flex-wrap gap-1.5"><UBadge v-for="form in webhook.forms" :key="form.id" :label="form.name" color="neutral" variant="soft" class="rounded-md" /></div>
            </div>
          </div>
          <IntegrationsWebhooksVerify v-else />
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
