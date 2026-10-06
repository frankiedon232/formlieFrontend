<!--
  An endpoint in a panel from the side (F13 M1, detail panel model): header with its address part,
  service and form, status and methods, ⋯ (open the form, the service, delete); a one-click bar
  (Answering on / off, Edit, Copy address); the full address; fact tiles; then Questions or Example
  (chips in a sliding row). Previous (K) · position · Next (J). Esc closes.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ApiEndpointDetail } from '#shared/types/apiService'

const props = defineProps<{ id: string | null; ids: string[]; busy: boolean }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string]; status: [endpoint: ApiEndpointDetail, active: boolean]; remove: [endpoint: ApiEndpointDetail]; copy: [endpoint: ApiEndpointDetail] }>()
const { t } = useI18n()
const api = useApi()
const { number, percent, relative } = useFormat()

const endpoint = ref<ApiEndpointDetail | null>(null)
const failed = ref(false)
async function load(id: string) {
  failed.value = false
  try {
    const { data } = await api.get<ApiEndpointDetail>(`/api-endpoints/${id}`)
    if (props.id === id) endpoint.value = data
  } catch {
    failed.value = true
  }
}
watch(() => [props.id, open.value] as const, ([id, isOpen]) => id && isOpen && void load(id), { immediate: true })
defineExpose({ reload: () => props.id && load(props.id) })

const index = computed(() => (props.id ? props.ids.indexOf(props.id) : -1))
const prev = computed(() => (index.value > 0 ? props.ids[index.value - 1] : null))
const next = computed(() => (index.value >= 0 && index.value < props.ids.length - 1 ? props.ids[index.value + 1] : null))
defineShortcuts({
  j: { usingInput: false, handler: () => open.value && next.value && emit('go', next.value) },
  k: { usingInput: false, handler: () => open.value && prev.value && emit('go', prev.value) },
})

const writes = computed(() => !!endpoint.value?.methods.some(method => method === 'POST' || method === 'PUT'))
const reads = computed(() => !!endpoint.value?.methods.includes('GET'))
const tiles = computed(() => {
  const e = endpoint.value
  if (!e) return []
  return [
    { key: 'calls', icon: 'i-lucide-arrow-left-right', label: t('apiService.col.calls'), value: number(e.calls_30d) },
    { key: 'errors', icon: 'i-lucide-octagon-alert', label: t('apiService.col.errors'), value: percent(e.calls_30d ? e.errors_30d / e.calls_30d : 0, 1) },
    { key: 'time', icon: 'i-lucide-timer', label: t('apiService.kpi.time'), value: e.avg_ms == null ? '–' : t('dataSources.ms', { n: e.avg_ms }) },
    { key: 'last', icon: 'i-lucide-clock', label: t('apiService.col.lastCall'), value: e.last_call_at ? relative(e.last_call_at) : t('apiService.neverCalled') },
    { key: 'version', icon: 'i-lucide-git-commit-horizontal', label: t('apiService.col.version'), value: e.version ? t('apiService.versionN', { n: e.version }) : t('apiService.latestVersion') },
    { key: 'page', icon: 'i-lucide-rows-3', label: t('apiService.pageSize'), value: reads.value ? number(e.page_size) : '–' },
  ]
})
const tab = ref<'fields' | 'example'>('fields')
const consoleOpen = ref(false)
const chips = computed(() => [
  { key: 'fields' as const, label: t('apiService.fields.title'), count: endpoint.value?.fields.length ?? 0 },
  { key: 'example' as const, label: t('apiService.call.title'), count: endpoint.value?.methods.length ?? 0 },
])
const menu = computed<DropdownMenuItem[][]>(() => {
  const e = endpoint.value
  if (!e) return []
  return [
    [
      { label: t('apiService.actions.openForm'), icon: 'i-lucide-file-text', to: `/forms/${e.form.id}` },
      { label: t('apiService.actions.openService'), icon: 'i-lucide-boxes', to: { path: '/api-service/services', query: { service: e.service.id } } },
    ],
    [{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => emit('remove', e) }],
  ]
})
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="endpoint ? `/${endpoint.name}` : t('nav.apiEndpoints')"
    :ui="{ content: 'w-full sm:max-w-2xl', header: 'border-b-0 pb-2', body: 'flex flex-col gap-6 pb-40', footer: 'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4' }"
  >
    <template #header>
      <div v-if="!endpoint" class="flex w-full items-center gap-3.5">
        <USkeleton class="size-14 rounded-2xl" />
        <div class="flex flex-1 flex-col gap-2"><USkeleton class="h-5 w-48" /><USkeleton class="h-4 w-32" /></div>
      </div>
      <div v-else class="flex w-full flex-col gap-4">
        <div class="flex items-start gap-3.5">
          <span class="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-inverted text-inverted"><UIcon name="i-lucide-route" class="size-6" /></span>
          <div class="flex min-w-0 flex-1 flex-col gap-1">
            <h2 class="truncate font-mono text-lg leading-tight font-semibold text-highlighted" dir="ltr">/{{ endpoint.name }}</h2>
            <p class="truncate text-sm text-muted">{{ endpoint.service.name }} · {{ endpoint.form.name }}</p>
            <div class="mt-1 flex flex-wrap items-center gap-1.5">
              <DataStatusBadge :status="endpoint.status" />
              <ApiMethods :methods="endpoint.methods" size="xs" />
              <UBadge v-if="endpoint.service.status !== 'active'" :label="t('apiService.serviceOff')" icon="i-lucide-circle-pause" color="warning" variant="subtle" size="sm" class="rounded-md" />
              <UBadge v-if="endpoint.form.status !== 'published'" :label="t('apiService.formNotPublished')" icon="i-lucide-triangle-alert" color="warning" variant="subtle" size="sm" class="rounded-md" />
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
          <USwitch :model-value="endpoint.status === 'active'" :label="endpoint.status === 'active' ? t('apiService.setup.isLive') : t('apiService.setup.notLive')" :disabled="busy" @update:model-value="value => emit('status', endpoint!, !!value)" />
          <span class="mx-1 h-5 w-px bg-(--ui-border)" aria-hidden="true" />
          <UButton :label="t('apiService.actions.edit')" icon="i-lucide-pencil" color="neutral" size="sm" :to="`/api-service/endpoints/${endpoint.id}/edit`" />
          <UButton :label="t('apiService.actions.copyUrl')" icon="i-lucide-link" color="neutral" variant="outline" size="sm" @click="emit('copy', endpoint)" />
          <UButton :label="t('apiService.docs.test')" icon="i-lucide-play" color="neutral" variant="outline" size="sm" :disabled="!endpoint.setup.service_active || !endpoint.setup.form_published" @click="consoleOpen = true" />
        </div>
      </div>
    </template>

    <template #body>
      <AppEmpty v-if="failed && !endpoint" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" />
      <div v-else-if="!endpoint" class="flex flex-col gap-4">
        <USkeleton class="h-9 w-full" />
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <USkeleton v-for="n in 6" :key="n" class="h-14 rounded-lg" />
        </div>
      </div>
      <template v-else>
        <AppCopyField :value="endpoint.url" :label="t('apiService.address')" monospace />
        <ApiEndpointsSetup v-if="!endpoint.setup.live || !endpoint.setup.tokens_live" :endpoint="endpoint" :busy="busy" @test="consoleOpen = true" @live="on => emit('status', endpoint!, on)" />
        <div class="grid grid-cols-2 gap-2 transition-opacity sm:grid-cols-3" :class="busy ? 'opacity-60' : ''">
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
            <UButton
              v-for="chip in chips"
              :key="chip.key"
              role="tab"
              :aria-selected="tab === chip.key"
              :label="chip.label"
              color="neutral"
              :variant="tab === chip.key ? 'solid' : 'outline'"
              size="sm"
              class="shrink-0 rounded-full"
              @click="tab = chip.key"
            >
              <template #trailing><span class="text-xs tabular-nums opacity-70">{{ chip.count }}</span></template>
            </UButton>
          </div>
          <ApiEndpointsFields v-if="tab === 'fields'" :fields="endpoint.fields" :writes="writes" :reads="reads" />
          <ApiEndpointsExample v-else :methods="endpoint.methods" :url="endpoint.url" :fields="endpoint.fields" :page-size="endpoint.page_size" />
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
  <ApiDocsConsole v-model:open="consoleOpen" :endpoint="endpoint" />
</template>
