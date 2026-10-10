<!--
  A service in a panel from the side (F13 M1, detail panel model): header with its status and ⋯
  (duplicate, delete), a one-click bar (Answering on / off, New endpoint, Edit); fact tiles; calls
  per day; its endpoints as two-column tiles (each opens on Endpoints). Previous (K) · Next (J).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ApiEndpoint, ApiService } from '#shared/types/apiService'

const props = defineProps<{ id: string | null; ids: string[]; busy: boolean }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string]; edit: [service: ApiService]; status: [service: ApiService, active: boolean]; duplicate: [service: ApiService]; remove: [service: ApiService] }>()
const { t, d } = useI18n()
const api = useApi()
const { number, percent, relative, date } = useFormat()
const { can } = useCan()

const service = ref<ApiService | null>(null)
const endpoints = ref<ApiEndpoint[] | null>(null)
const failed = ref(false)
async function load(id: string) {
  failed.value = false
  try {
    const [one, list] = await Promise.all([api.get<ApiService>(`/api-services/${id}`), api.list<ApiEndpoint>('/api-endpoints', { 'filter[service]': id, page_size: 100, sort: 'name' })])
    if (props.id !== id) return
    service.value = one.data
    endpoints.value = list.data
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

const trend = computed(() => (service.value?.previous_30d ? Math.round(((service.value.calls_30d - service.value.previous_30d) / service.value.previous_30d) * 100) : null))
const tiles = computed(() => {
  const s = service.value
  if (!s) return []
  return [
    { key: 'endpoints', icon: 'i-lucide-route', label: t('apiService.col.endpoints'), value: number(s.endpoints_count) },
    { key: 'calls', icon: 'i-lucide-arrow-left-right', label: t('apiService.col.calls'), value: number(s.calls_30d) },
    { key: 'errors', icon: 'i-lucide-octagon-alert', label: t('apiService.col.errors'), value: percent(s.calls_30d ? s.errors_30d / s.calls_30d : 0, 1) },
    { key: 'time', icon: 'i-lucide-timer', label: t('apiService.kpi.time'), value: s.avg_ms == null ? '–' : t('dataSources.ms', { n: s.avg_ms }) },
    { key: 'last', icon: 'i-lucide-clock', label: t('apiService.col.lastCall'), value: s.last_call_at ? relative(s.last_call_at) : t('apiService.neverCalled') },
    { key: 'by', icon: 'i-lucide-user-round', label: t('apiService.createdBy'), value: `${s.created_by.name} · ${date(s.created_at)}` },
  ]
})
const points = computed(() => (service.value?.daily ?? []).map(day => ({ label: d(new Date(`${day.date}T12:00:00`), { day: 'numeric', month: 'short' }), value: day.count })))
const menu = computed<DropdownMenuItem[][]>(() =>
  service.value
    ? [
        [
          { label: t('apiService.actions.viewEndpoints'), icon: 'i-lucide-route', to: { path: '/api-service/endpoints', query: { service: service.value.id } } },
          ...(can('api.service_create') ? [{ label: t('apiService.actions.duplicate'), icon: 'i-lucide-copy', onSelect: () => emit('duplicate', service.value!) }] : []),
        ],
        service.value.can?.delete ? [{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => emit('remove', service.value!) }] : [],
      ].filter(group => group.length)
    : [],
)
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="service?.name || t('nav.apiServices')"
    :ui="{ content: 'w-full sm:max-w-2xl', header: 'border-b-0 pb-2', body: 'flex flex-col gap-6 pb-40', footer: 'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4' }"
  >
    <template #header>
      <div v-if="!service" class="flex w-full items-center gap-3.5">
        <USkeleton class="size-14 rounded-2xl" />
        <div class="flex flex-1 flex-col gap-2"><USkeleton class="h-5 w-48" /><USkeleton class="h-4 w-32" /></div>
      </div>
      <div v-else class="flex w-full flex-col gap-4">
        <div class="flex items-start gap-3.5">
          <span class="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-inverted text-inverted"><UIcon name="i-lucide-boxes" class="size-6" /></span>
          <div class="flex min-w-0 flex-1 flex-col gap-1">
            <h2 class="truncate text-lg leading-tight font-semibold text-highlighted">{{ service.name }}</h2>
            <p class="line-clamp-2 text-sm text-muted">{{ service.description || t('apiService.noDescription') }}</p>
            <div class="mt-1 flex flex-wrap items-center gap-1.5"><DataStatusBadge :status="service.status" /><ApiMethods :methods="service.methods" size="xs" /></div>
          </div>
          <div class="flex shrink-0 items-center gap-1">
            <UDropdownMenu :items="menu" :content="{ align: 'end' }">
              <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="sm" square :aria-label="t('dataView.actions')" />
            </UDropdownMenu>
            <UButton icon="i-lucide-x" color="neutral" variant="soft" size="sm" square class="rounded-full" :aria-label="t('common.close')" @click="open = false" />
          </div>
        </div>
        <div v-if="service.can?.edit || can('api.endpoints')" class="flex flex-wrap items-center gap-2">
          <USwitch v-if="service.can?.edit" :model-value="service.status === 'active'" :label="t('apiService.answering')" :disabled="busy" @update:model-value="value => emit('status', service!, !!value)" />
          <span v-if="service.can?.edit && can('api.endpoints')" class="mx-1 h-5 w-px bg-(--ui-border)" aria-hidden="true" />
          <UButton v-if="can('api.endpoints')" :label="t('apiService.actions.newEndpoint')" icon="i-lucide-plus" color="neutral" size="sm" :to="{ path: '/api-service/endpoints/new', query: { service: service.id } }" />
          <UButton v-if="service.can?.edit" :label="t('apiService.actions.edit')" icon="i-lucide-pencil" color="neutral" variant="outline" size="sm" @click="emit('edit', service)" />
        </div>
      </div>
    </template>

    <template #body>
      <AppEmpty v-if="failed && !service" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" />
      <div v-else-if="!service" class="flex flex-col gap-4"><div class="grid grid-cols-2 gap-2 sm:grid-cols-3"><USkeleton v-for="n in 6" :key="n" class="h-14 rounded-lg" /></div><USkeleton class="h-40 w-full" /></div>
      <template v-else>
        <div class="grid grid-cols-2 gap-2 transition-opacity sm:grid-cols-3" :class="busy ? 'opacity-60' : ''">
          <div v-for="tile in tiles" :key="tile.key" class="flex min-w-0 items-center gap-2.5 rounded-lg border border-default p-2.5">
            <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="tile.icon" class="size-4 text-muted" /></span>
            <div class="flex min-w-0 flex-col">
              <span class="truncate text-[11px] text-muted">{{ tile.label }}</span>
              <span class="truncate text-sm font-semibold text-highlighted tabular-nums">{{ tile.value }}</span>
            </div>
          </div>
        </div>
        <ApiConnections :id="service.id" type="service" />

        <section class="flex flex-col gap-3">
          <div class="flex items-center gap-2">
            <h3 class="text-sm font-semibold text-highlighted">{{ t('apiService.kpi.calls') }}</h3>
            <UBadge v-if="trend !== null" :label="`${trend > 0 ? '+' : ''}${trend}%`" :color="trend >= 0 ? 'success' : 'error'" variant="subtle" size="sm" class="rounded-md tabular-nums" />
          </div>
          <ChartsBars v-if="service.calls_30d" :points="points" height="h-32" :unit="n => t('apiService.callsCount', { n: number(n) }, n)" />
          <p v-else class="text-sm text-muted">{{ t('apiService.noCalls') }}</p>
        </section>

        <section class="flex flex-col gap-3">
          <h3 class="text-sm font-semibold text-highlighted">{{ t('apiService.col.endpoints') }}</h3>
          <div v-if="!endpoints" class="grid gap-2 sm:grid-cols-2"><USkeleton v-for="n in 2" :key="n" class="h-20 rounded-lg" /></div>
          <AppEmpty v-else-if="!endpoints.length" size="xs" icon="i-lucide-route" :title="t('apiService.noEndpoints')" :actions="can('api.endpoints') ? [{ label: t('apiService.actions.newEndpoint'), icon: 'i-lucide-plus', color: 'neutral', to: { path: '/api-service/endpoints/new', query: { service: service.id } } }] : []" />
          <div v-else class="grid gap-2 sm:grid-cols-2">
            <NuxtLink
              v-for="endpoint in endpoints"
              :key="endpoint.id"
              :to="{ path: '/api-service/endpoints', query: { endpoint: endpoint.id } }"
              class="flex h-full flex-col gap-2 rounded-lg border border-default p-3 transition-colors hover:border-accented hover:bg-elevated/40 focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="truncate font-mono text-sm font-semibold text-highlighted" dir="ltr">/{{ endpoint.name }}</span>
                <DataStatusBadge :status="endpoint.status" />
              </div>
              <span class="flex min-w-0 items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-file-text" class="size-3.5 shrink-0" /><span class="truncate">{{ endpoint.form.name }}</span></span>
              <div class="mt-auto flex items-center justify-between gap-2">
                <ApiMethods :methods="endpoint.methods" size="xs" />
                <span class="text-xs text-muted tabular-nums">{{ t('apiService.callsCount', { n: number(endpoint.calls_30d) }, endpoint.calls_30d) }}</span>
              </div>
            </NuxtLink>
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
