<!--
  One logged call in a panel from the side (F13 M4, detail panel model): the method, address and
  status; fact tiles (when, time taken, endpoint, token, caller, request id); then Headers and the
  kept bodies (personal answers masked) in a sliding row of chips. Previous (K) · Next (J).
-->
<script setup lang="ts">
import type { ApiLogDetail } from '#shared/types/apiService'

const props = defineProps<{ id: string | null; ids: string[] }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string] }>()
const { t } = useI18n()
const api = useApi()
const { dateTime } = useFormat()
const { current } = useAppLocale()
const { copy } = useClipboard({ legacy: true })
const toast = useToast()

const log = ref<ApiLogDetail | null>(null)
const failed = ref(false)
async function load(id: string) {
  failed.value = false
  try {
    const { data } = await api.get<ApiLogDetail>(`/api-logs/${id}`)
    if (props.id === id) log.value = data
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
const country = (code: string | null) => (code ? (new Intl.DisplayNames([current.value.language], { type: 'region' }).of(code) ?? code) : t('apiService.logs.unknownCountry'))
const tiles = computed(() => {
  const l = log.value
  if (!l) return []
  return [
    { key: 'at', icon: 'i-lucide-clock', label: t('apiService.logs.col.at'), value: dateTime(l.at) },
    { key: 'duration', icon: 'i-lucide-timer', label: t('apiService.logs.col.duration'), value: t('dataSources.ms', { n: l.duration_ms }) },
    { key: 'endpoint', icon: 'i-lucide-route', label: t('apiService.col.endpoint'), value: l.endpoint ? `/${l.endpoint.name}` : t('apiService.logs.noEndpoint') },
    { key: 'token', icon: 'i-lucide-key-round', label: t('apiService.logs.col.token'), value: l.token ? `${l.token.name} · ${t(`apiService.tokens.mode.${l.token.mode}`)}` : t('apiService.logs.noToken') },
    { key: 'caller', icon: 'i-lucide-network', label: t('apiService.logs.col.caller'), value: `${l.ip} · ${country(l.country)}` },
    { key: 'agent', icon: 'i-lucide-terminal', label: t('apiService.logs.col.agent'), value: l.user_agent || '–' },
  ]
})
const tab = ref<'headers' | 'request' | 'response'>('headers')
watch(() => props.id, () => (tab.value = 'headers'))
const chips = computed(() => [
  { key: 'headers' as const, label: t('apiService.logs.headers') },
  { key: 'request' as const, label: t('apiService.logs.request') },
  { key: 'response' as const, label: t('apiService.logs.response') },
])
const json = (value: unknown) => JSON.stringify(value, null, 2)
function copyId() {
  if (!log.value) return
  void copy(log.value.request_id)
  toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
}
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="log ? `${log.method} ${log.path}` : t('nav.apiLogs')"
    :ui="{ content: 'w-full sm:max-w-2xl', header: 'border-b-0 pb-2', body: 'flex flex-col gap-6 pb-40', footer: 'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4' }"
  >
    <template #header>
      <div v-if="!log" class="flex w-full items-center gap-3.5">
        <USkeleton class="size-14 rounded-2xl" />
        <div class="flex flex-1 flex-col gap-2"><USkeleton class="h-5 w-48" /><USkeleton class="h-4 w-32" /></div>
      </div>
      <div v-else class="flex w-full items-start gap-3.5">
        <span class="flex size-14 shrink-0 items-center justify-center rounded-2xl" :class="log.status >= 400 ? (log.status >= 500 ? 'bg-error/10 text-error' : 'bg-warning/10 text-warning') : 'bg-inverted text-inverted'"><UIcon name="i-lucide-scroll-text" class="size-6" /></span>
        <div class="flex min-w-0 flex-1 flex-col gap-1">
          <h2 class="truncate font-mono text-base leading-tight font-semibold text-highlighted" dir="ltr">{{ log.method }} {{ log.path }}</h2>
          <p class="text-sm text-muted">{{ log.code ? t(`errors.${log.code}`) : t('apiService.logs.ok') }}</p>
          <div class="mt-1 flex flex-wrap items-center gap-1.5">
            <ApiLogsStatus :status="log.status" :code="log.code" />
            <UBadge v-if="log.code" :label="log.code" color="neutral" variant="outline" size="sm" class="rounded-md font-mono" />
          </div>
        </div>
        <div class="flex shrink-0 items-center gap-1">
          <UButton icon="i-lucide-copy" color="neutral" variant="ghost" size="sm" square :aria-label="t('apiService.logs.copyId')" @click="copyId" />
          <UButton icon="i-lucide-x" color="neutral" variant="soft" size="sm" square class="rounded-full" :aria-label="t('common.close')" @click="open = false" />
        </div>
      </div>
    </template>

    <template #body>
      <AppEmpty v-if="failed && !log" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" />
      <div v-else-if="!log" class="grid grid-cols-2 gap-2 sm:grid-cols-3"><USkeleton v-for="n in 6" :key="n" class="h-14 rounded-lg" /></div>
      <template v-else>
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <div v-for="tile in tiles" :key="tile.key" class="flex min-w-0 items-center gap-2.5 rounded-lg border border-default p-2.5">
            <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="tile.icon" class="size-4 text-muted" /></span>
            <div class="flex min-w-0 flex-col">
              <span class="truncate text-[11px] text-muted">{{ tile.label }}</span>
              <span class="truncate text-sm font-semibold text-highlighted tabular-nums" :title="tile.value">{{ tile.value }}</span>
            </div>
          </div>
        </div>
        <p class="truncate font-mono text-xs text-muted" dir="ltr">{{ t('apiService.logs.requestId') }}: {{ log.request_id }}</p>

        <section class="flex flex-col gap-3">
          <div class="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1" role="tablist">
            <UButton v-for="chip in chips" :key="chip.key" role="tab" :aria-selected="tab === chip.key" :label="chip.label" color="neutral" :variant="tab === chip.key ? 'solid' : 'outline'" size="sm" class="shrink-0 rounded-full" @click="tab = chip.key" />
          </div>
          <template v-if="tab === 'headers'">
            <AppEmpty v-if="!Object.keys(log.request_headers).length" size="xs" icon="i-lucide-heading" :title="t('apiService.logs.noHeaders')" />
            <ul v-else class="divide-y divide-default overflow-hidden rounded-lg border border-default">
              <li v-for="(value, name) in log.request_headers" :key="name" class="flex flex-col gap-0.5 px-3 py-2 sm:flex-row sm:gap-4">
                <code class="w-48 shrink-0 font-mono text-xs font-medium text-highlighted" dir="ltr">{{ name }}</code>
                <code class="min-w-0 flex-1 truncate font-mono text-xs text-muted" dir="ltr">{{ value }}</code>
              </li>
            </ul>
          </template>
          <template v-else>
            <AppEmpty v-if="!log.bodies_kept" size="xs" icon="i-lucide-eye-off" :title="t('apiService.logs.notKept')" :description="t('apiService.logs.notKeptDesc')" />
            <pre v-else class="max-h-96 overflow-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-default" dir="ltr">{{ json(tab === 'request' ? log.request_body : log.response_body) }}</pre>
          </template>
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
