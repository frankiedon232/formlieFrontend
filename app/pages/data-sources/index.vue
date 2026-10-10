<!--
  Data sources overview (own rail area, F12; the design's dashboard, docs/design 092034): five KPI
  cards (connections, forms storing in a database, responses delivered, operations, what needs a
  look), database traffic beside one connection at a time, recent activity, and the supported
  databases with every section one click away. Without connections: what Data sources is for and
  Add connection.
-->
<script setup lang="ts">
import type { DataSourceInsights, DataSourceRow } from '#shared/types/datasources'
import type { DestinationInsights } from '#shared/types/destinations'
import type { ActivityInsights } from '#shared/utils/datasources/activity'
import { SUPPORTED_DATABASES } from '#shared/utils/integrations/databases'

definePageMeta({ breadcrumb: 'nav.dataSources' })
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { number } = useFormat()
const { can } = useCan()
useHead({ title: () => t('nav.dataSources') })

const insights = ref<DataSourceInsights | null>(null)
const deliveries = ref<DestinationInsights | null>(null)
const activity = ref<ActivityInsights | null>(null)
const sources = ref<DataSourceRow[] | null>(null)
onMounted(async () => {
  try {
    const [a, b, c, d] = await Promise.all([
      api.get<DataSourceInsights>('/datasources/insights'),
      api.get<DestinationInsights>('/destinations/insights'),
      api.get<ActivityInsights>('/datasources/activity/insights'),
      api.list<DataSourceRow>('/datasources', { page_size: 100, sort: 'name' }),
    ])
    insights.value = a.data
    deliveries.value = b.data
    activity.value = c.data
    sources.value = d.data
  } catch (error) {
    handle(error)
    sources.value ??= []
  }
})

const change = (now?: number, before?: number) => (now != null && before ? Math.round(((now - before) / before) * 100) : null)
const needLook = computed(() => (insights.value && deliveries.value ? insights.value.by_status.attention + insights.value.by_status.failing + deliveries.value.deliveries.failed : null))
const kpis = computed(() => {
  const s = insights.value
  const dl = deliveries.value
  return [
    { key: 'connections', icon: 'i-lucide-database', label: t('nav.dataConnections'), value: s ? number(s.total) : null, hint: s ? t('dataSources.home.connected', { n: number(s.by_status.connected) }) : '', to: '/data-sources/connections' },
    { key: 'forms', icon: 'i-lucide-file-input', label: t('dataSources.home.formsStoring'), value: dl ? number(dl.total) : null, hint: t('dataSources.home.inDatabases'), to: '/data-sources/destinations' },
    { key: 'delivered', icon: 'i-lucide-send', label: t('dataSources.home.deliveredLabel'), value: dl ? number(dl.sent_30d) : null, change: change(dl?.sent_30d, dl?.previous_30d), to: '/data-sources/destinations' },
    { key: 'operations', icon: 'i-lucide-activity', label: t('dataSources.home.allOperations'), value: s ? number(s.operations_30d) : null, change: change(s?.operations_30d, s?.previous_30d), to: '/data-sources/activity' },
    { key: 'look', icon: 'i-lucide-triangle-alert', label: t('dataSources.needsLook'), value: needLook.value == null ? null : number(needLook.value), hint: t('dataSources.home.lookHint'), to: { path: '/data-sources/connections', query: { status: 'attention,failing' } } },
  ]
})

// Only the sections the role can open
const shortcuts = computed(() =>
  [
    { key: 'explorer', nav: 'dataExplorer', icon: 'i-lucide-table-2', to: '/data-sources/explorer', show: can('data.browse') },
    { key: 'query', nav: 'dataQuery', icon: 'i-lucide-square-terminal', to: '/data-sources/query', show: can('data.query') },
    { key: 'savedQueries', nav: 'dataSavedQueries', icon: 'i-lucide-bookmark', to: '/data-sources/saved-queries', show: true },
    { key: 'destinations', nav: 'destinations', icon: 'i-lucide-send', to: '/data-sources/destinations', show: true },
  ].filter(item => item.show),
)
</script>

<template>
  <AppPanel id="data-sources" :title="t('nav.dataSources')" :subtitle="t('dataSources.subtitle')" subtitle-icon="i-lucide-database">
    <template #actions>
      <UButton v-if="can('data.query')" :label="t('nav.dataQuery')" icon="i-lucide-square-terminal" color="neutral" variant="outline" to="/data-sources/query" class="hidden sm:inline-flex" />
      <UButton v-if="can('data.create')" :label="t('dataSources.add')" icon="i-lucide-plus" color="neutral" to="/data-sources/connections/new" />
    </template>

    <AppEmpty
      v-if="sources && !sources.length"
      icon="i-lucide-database"
      :title="t('dataSources.emptyTitle')"
      :description="t('dataSources.emptyDesc')"
      :actions="can('data.create') ? [{ label: t('dataSources.add'), icon: 'i-lucide-plus', color: 'neutral', to: '/data-sources/connections/new' }] : []"
    />
    <template v-else>
      <div class="flex shrink-0 snap-x gap-3 overflow-x-auto [scrollbar-width:none] sm:grid sm:grid-cols-3 sm:overflow-visible xl:grid-cols-5">
        <ChartsKpi
          v-for="kpi in kpis"
          :key="kpi.key"
          class="min-w-[13.5rem] snap-start sm:min-w-0"
          :label="kpi.label"
          :icon="kpi.icon"
          :value="kpi.value"
          :change="'change' in kpi ? kpi.change : null"
          :hint="'hint' in kpi ? kpi.hint : undefined"
          :lower-is-better="kpi.key === 'look'"
          :to="kpi.to"
        />
      </div>

      <div class="grid shrink-0 gap-4 lg:grid-cols-3">
        <DatasourcesHomeTraffic class="lg:col-span-2" :sources="insights" :deliveries="deliveries" :activity="activity" />
        <DatasourcesHomeConnection :sources="sources" />
      </div>

      <DatasourcesHomeRecent class="shrink-0" />
    </template>

    <div class="grid shrink-0 gap-4 lg:grid-cols-3">
      <UCard variant="outline" class="lg:col-span-2" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
        <div>
          <h2 class="text-sm font-semibold text-highlighted">{{ t('dataSources.engines') }}</h2>
          <p class="text-xs text-muted">{{ t('dataSources.enginesHint') }}</p>
        </div>
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <div v-for="db in SUPPORTED_DATABASES" :key="db.key" class="flex min-w-0 items-center gap-2.5 rounded-lg border border-default p-2.5">
            <DatasourcesEngineLogo :engine="db.key" size="sm" />
            <span class="truncate text-sm font-medium text-highlighted">{{ db.name }}</span>
          </div>
          <div class="flex min-w-0 items-center gap-2.5 rounded-lg border border-dashed border-default p-2.5">
            <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-inverted text-inverted"><UIcon name="i-lucide-shield-check" class="size-4" /></span>
            <span class="truncate text-sm font-medium text-highlighted">{{ t('dataSources.builtIn') }}</span>
          </div>
        </div>
      </UCard>
      <UCard variant="outline" :ui="{ body: 'flex flex-col gap-2 p-4 sm:p-5' }">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('dataSources.home.shortcuts') }}</h2>
        <NuxtLink
          v-for="item in shortcuts"
          :key="item.key"
          :to="item.to"
          class="group flex items-center gap-3 rounded-lg p-2 transition-colors hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
        >
          <span class="flex size-8 shrink-0 items-center justify-center rounded-md border border-default"><UIcon :name="item.icon" class="size-4 text-highlighted" /></span>
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="truncate text-sm font-medium text-highlighted">{{ t(`nav.${item.nav}`) }}</span>
            <span class="truncate text-xs text-muted">{{ t(`dataSources.section.${item.key}`) }}</span>
          </span>
          <UIcon name="i-lucide-arrow-up-right" class="size-4 shrink-0 text-muted group-hover:text-highlighted rtl:-scale-x-100" />
        </NuxtLink>
      </UCard>
    </div>
  </AppPanel>
</template>
