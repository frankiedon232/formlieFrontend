<!--
  Dashboard → Data sources view (F21 M3): the connections at work, for people with data access. KPI cards
  (connections, operations, responses stored, failing, response time); operations over time beside each
  connection's health; then what people did (queries, rows, structure, exports, storage, connections), response
  storage (sent, waiting, failed) and the latest data activity from the audit trail.
-->
<script setup lang="ts">
import type { DashboardGroup, DataDashboard } from '#shared/types/dashboard'
import { ACTIVITY_COLOR, ACTIVITY_KINDS } from '#shared/utils/datasources/activity'

const props = defineProps<{ from: string; to: string; group?: DashboardGroup }>()
const emit = defineEmits<{ loaded: [group: DashboardGroup] }>()
const { t, d } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { number, relative } = useFormat()

const data = ref<DataDashboard | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    data.value = (await api.get<DataDashboard>('/dashboard/data', { from: props.from, to: props.to, group: props.group })).data
    emit('loaded', data.value.group)
  } catch (error) {
    failed.value = true
    handle(error)
  }
}
watch(() => [props.from, props.to, props.group], load, { immediate: true })
defineExpose({ refresh: load })

const change = (kpi: { value: number; previous: number | null } | undefined) => (kpi && kpi.previous ? Math.round(((kpi.value - kpi.previous) / kpi.previous) * 100) : null)
const kpis = computed(() => {
  const k = data.value?.kpis
  return [
    { key: 'connections', icon: 'i-lucide-database', label: t('dashboard.dataView.connections'), value: k ? number(k.connections.value) : null, change: null, to: '/data-sources/connections', hint: t('dashboard.dataView.connectionsHint') },
    { key: 'operations', icon: 'i-lucide-activity', label: t('dashboard.dataView.operations'), value: k ? number(k.operations.value) : null, change: change(k?.operations), to: '/data-sources/activity' },
    { key: 'deliveries', icon: 'i-lucide-hard-drive-download', label: t('dashboard.dataView.stored'), value: k ? number(k.deliveries.value) : null, change: change(k?.deliveries), to: '/data-sources/destinations' },
    { key: 'failing', icon: 'i-lucide-database-zap', label: t('dashboard.dataView.failing'), value: k ? number(k.failing.value) : null, change: null, to: '/data-sources/connections', hint: k?.failing.value ? t('dashboard.dataView.failingHint') : t('dashboard.kpi.allGood'), lower: true },
    { key: 'latency', icon: 'i-lucide-timer', label: t('dashboard.dataView.latency'), value: k ? (k.latency.value ? `${number(k.latency.value)} ms` : '–') : null, change: null, to: '/data-sources/connections', hint: t('dashboard.dataView.latencyHint'), lower: true },
  ]
})

const bucketLabel = (start: string) => {
  const day = new Date(`${start}T00:00:00Z`)
  const group = data.value?.group ?? 'day'
  return group === 'year' ? String(day.getUTCFullYear()) : group === 'month' ? d(day, { month: 'short', year: '2-digit', timeZone: 'UTC' }) : d(day, { day: 'numeric', month: 'short', timeZone: 'UTC' })
}
const points = computed(() => data.value?.series.map(item => ({ label: bucketLabel(item.start), value: item.operations, hint: t('dashboard.dataView.storedIn', { n: number(item.deliveries) }) })) ?? [])
const anyOps = computed(() => points.value.some(point => point.value))
const kinds = computed(() => ACTIVITY_KINDS.map(key => ({ key, count: data.value?.kinds[key] ?? 0, color: ACTIVITY_COLOR[key] })))
const kindTotal = computed(() => kinds.value.reduce((sum, item) => sum + item.count, 0))
const storageTotal = computed(() => (data.value ? data.value.storage.sent + data.value.storage.pending + data.value.storage.failed : 0))
const actionLabel = (action: string) => t(`audit.action.${action.replace(/\./g, '_')}`)
</script>

<template>
  <AppEmpty v-if="failed && !data" icon="i-lucide-cloud-off" :title="t('dashboard.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
  <div v-else class="flex flex-col gap-4" :class="data && failed ? 'opacity-60' : ''">
    <div class="flex shrink-0 snap-x gap-3 overflow-x-auto [scrollbar-width:none] sm:grid sm:grid-cols-3 sm:overflow-visible xl:grid-cols-5">
      <ChartsKpi v-for="kpi in kpis" :key="kpi.key" class="min-w-[13.5rem] snap-start sm:min-w-0" :label="kpi.label" :icon="kpi.icon" :value="kpi.value" :change="kpi.change" :hint="kpi.hint" :to="kpi.to" :lower-is-better="!!kpi.lower" />
    </div>

    <AppEmpty v-if="data && !data.kpis.connections.value" icon="i-lucide-database" :title="t('dashboard.dataView.noneTitle')" :description="t('dashboard.dataView.noneDesc')" :actions="[{ label: t('dashboard.dataView.add'), icon: 'i-lucide-plus', color: 'neutral', to: '/data-sources/connections/new' }]" />
    <template v-else>
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <UCard variant="outline" class="min-w-0 lg:col-span-2" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
          <div class="flex flex-col gap-1">
            <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.dataView.activity') }}</h2>
            <span v-if="data" class="flex items-center gap-2 border-s-2 border-default ps-3">
              <span class="text-2xl font-semibold text-highlighted tabular-nums">{{ t('dashboard.dataView.operationsCount', { n: number(data.kpis.operations.value) }, data.kpis.operations.value) }}</span>
              <UBadge v-if="change(data.kpis.operations) !== null" :label="`${change(data.kpis.operations)! >= 0 ? '+' : ''}${change(data.kpis.operations)}%`" :color="change(data.kpis.operations)! >= 0 ? 'success' : 'error'" variant="subtle" size="sm" />
            </span>
            <USkeleton v-else class="h-9 w-48" />
          </div>
          <USkeleton v-if="!data" class="h-48 w-full" />
          <p v-else-if="!anyOps" class="text-sm text-muted">{{ t('dashboard.dataView.noOps') }}</p>
          <ChartsBars v-else :points="points" :unit="n => t('dashboard.dataView.operationsCount', { n: number(n) }, n)" height="h-72" />
        </UCard>

        <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
          <div class="flex items-center gap-2">
            <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.dataView.health') }}</h2>
            <UButton icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" square class="ms-auto" to="/data-sources/connections" :aria-label="t('dashboard.dataView.connections')" />
          </div>
          <div v-if="!data" class="flex flex-col gap-2"><USkeleton v-for="n in 5" :key="n" class="h-10 w-full" /></div>
          <ul v-else class="flex flex-col divide-y divide-default">
            <li v-for="item in data.connections" :key="item.id">
              <NuxtLink :to="`/data-sources/connections/${item.id}`" class="flex items-center gap-3 py-2 hover:text-highlighted focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
                <DatasourcesEngineLogo :engine="item.engine" size="sm" />
                <span class="flex min-w-0 flex-1 flex-col">
                  <span class="truncate text-sm text-highlighted">{{ item.name }}</span>
                  <span class="truncate text-[11px] text-muted">{{ item.latency_ms !== null ? `${number(item.latency_ms)} ms` : '–' }} · {{ t('dashboard.dataView.operationsCount', { n: number(item.operations) }, item.operations) }}</span>
                </span>
                <DataStatusBadge :status="item.status" />
              </NuxtLink>
            </li>
          </ul>
        </UCard>
      </div>

      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.dataView.done') }}</h2>
          <div v-if="!data" class="flex flex-col gap-3"><USkeleton v-for="n in 4" :key="n" class="h-7 w-full" /></div>
          <p v-else-if="!kindTotal" class="text-xs text-muted">{{ t('dashboard.dataView.nothingDone') }}</p>
          <template v-else>
            <ChartsMeter v-for="item in kinds" :key="item.key" :label="t(`dataActivity.kind.${item.key}`)" :count="item.count" :total="kindTotal" />
          </template>
        </UCard>
        <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
          <div class="flex items-center gap-2">
            <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.dataView.storage') }}</h2>
            <UButton icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" square class="ms-auto" to="/data-sources/destinations" :aria-label="t('dashboard.dataView.storage')" />
          </div>
          <div v-if="!data" class="flex flex-col gap-3"><USkeleton v-for="n in 3" :key="n" class="h-7 w-full" /></div>
          <p v-else-if="!data.storage.forms" class="text-xs text-muted">{{ t('dashboard.dataView.noStorage') }}</p>
          <template v-else>
            <p class="text-xs text-muted">{{ t('dashboard.dataView.storageForms', { n: number(data.storage.forms) }, data.storage.forms) }}</p>
            <ChartsMeter :label="t('dashboard.dataView.sent')" icon="i-lucide-circle-check" :count="data.storage.sent" :total="storageTotal" strong />
            <ChartsMeter :label="t('dashboard.dataView.waiting')" icon="i-lucide-clock" :count="data.storage.pending" :total="storageTotal" />
            <ChartsMeter :label="t('dashboard.dataView.failedSend')" icon="i-lucide-circle-x" :count="data.storage.failed" :total="storageTotal" />
          </template>
        </UCard>
        <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
          <div class="flex items-center gap-2">
            <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.dataView.recent') }}</h2>
            <UButton icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" square class="ms-auto" to="/data-sources/activity" :aria-label="t('dashboard.dataView.recent')" />
          </div>
          <div v-if="!data" class="flex flex-col gap-2"><USkeleton v-for="n in 4" :key="n" class="h-9 w-full" /></div>
          <p v-else-if="!data.recent.length" class="text-xs text-muted">{{ t('dashboard.dataView.nothingDone') }}</p>
          <ul v-else class="flex flex-col divide-y divide-default">
            <li v-for="item in data.recent" :key="item.id" class="flex flex-col py-1.5">
              <span class="truncate text-sm text-highlighted">{{ actionLabel(item.action) }}<template v-if="item.resource"> · {{ item.resource }}</template></span>
              <span class="truncate text-[11px] text-muted">{{ item.actor }} · {{ relative(item.at) }}</span>
            </li>
          </ul>
        </UCard>
      </div>
    </template>
  </div>
</template>
