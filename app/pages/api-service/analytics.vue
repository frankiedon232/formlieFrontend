<!--
  API service → Analytics (F13 M4; the design's dashboard, like Forms → Analytics): Last 7 / 30 days
  in the header; five KPI cards (calls, error share, p50, p95, tokens used) with their change; the
  traffic flow chart beside one endpoint at a time; then the busiest endpoints, callers, countries
  and methods. Separate from the forms' analytics; the dashboards come in F21.
-->
<script setup lang="ts">
import type { ApiAnalytics } from '#shared/types/apiService'

definePageMeta({ breadcrumb: 'nav.apiAnalytics' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const { handle } = useErrorHandler()
const { number, percent } = useFormat()
useHead({ title: () => t('nav.apiAnalytics') })

const period = computed({ get: () => (route.query.period === '7d' ? '7d' : '30d'), set: value => void router.replace({ query: { ...route.query, period: value === '30d' ? undefined : value } }) })
const periods = computed(() => [
  { value: '7d', label: t('apiService.analytics.last7') },
  { value: '30d', label: t('apiService.analytics.last30') },
])
const analytics = ref<ApiAnalytics | null>(null)
watch(
  period,
  async value => {
    analytics.value = null
    try {
      analytics.value = (await api.get<ApiAnalytics>('/api-analytics', { period: value })).data
    } catch (error) {
      handle(error)
    }
  },
  { immediate: true },
)
const change = (now?: number | null, before?: number | null) => (now != null && before ? Math.round(((now - before) / before) * 100) : null)
const kpis = computed(() => {
  const a = analytics.value
  const share = (x?: { calls: number; errors: number }) => (x?.calls ? x.errors / x.calls : 0)
  return [
    { key: 'calls', icon: 'i-lucide-arrow-left-right', label: t('apiService.kpi.calls'), value: a ? number(a.totals.calls) : null, change: change(a?.totals.calls, a?.previous.calls), to: '/api-service/logs' },
    { key: 'errors', icon: 'i-lucide-octagon-alert', label: t('apiService.analytics.errorShare'), value: a ? percent(share(a.totals), 1) : null, change: a ? change(share(a.totals) * 1000, share(a.previous) * 1000) : null, lower: true, to: { path: '/api-service/logs', query: { class: '4xx,5xx' } } },
    { key: 'p50', icon: 'i-lucide-timer', label: t('apiService.analytics.p50'), value: a ? (a.totals.p50_ms == null ? '–' : t('dataSources.ms', { n: a.totals.p50_ms })) : null, change: change(a?.totals.p50_ms, a?.previous.p50_ms), lower: true },
    { key: 'p95', icon: 'i-lucide-gauge', label: t('apiService.analytics.p95'), value: a ? (a.totals.p95_ms == null ? '–' : t('dataSources.ms', { n: a.totals.p95_ms })) : null, change: change(a?.totals.p95_ms, a?.previous.p95_ms), lower: true },
    { key: 'tokens', icon: 'i-lucide-key-round', label: t('apiService.analytics.tokensUsed'), value: a ? number(a.totals.tokens_used) : null, change: null, to: '/api-service/auth' },
  ]
})
</script>

<template>
  <AppPanel id="api-analytics" :title="t('nav.apiAnalytics')" :subtitle="t('apiService.section.analytics')" subtitle-icon="i-lucide-chart-line">
    <template #actions>
      <UTabs v-model="period" :items="periods" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" :aria-label="t('apiService.analytics.period')" />
    </template>

    <div class="flex shrink-0 snap-x gap-3 overflow-x-auto [scrollbar-width:none] sm:grid sm:grid-cols-3 sm:overflow-visible xl:grid-cols-5">
      <ChartsKpi
        v-for="kpi in kpis"
        :key="kpi.key"
        class="min-w-[13.5rem] snap-start sm:min-w-0"
        :label="kpi.label"
        :icon="kpi.icon"
        :value="kpi.value"
        :change="kpi.change"
        :lower-is-better="'lower' in kpi"
        :to="'to' in kpi ? kpi.to : undefined"
      />
    </div>

    <div class="grid shrink-0 gap-4 lg:grid-cols-3">
      <ApiAnalyticsTraffic class="lg:col-span-2" :analytics="analytics" :change="change(analytics?.totals.calls, analytics?.previous.calls)" />
      <ApiAnalyticsEndpointFocus :analytics="analytics" />
    </div>

    <ApiAnalyticsBreakdown :analytics="analytics" />
  </AppPanel>
</template>
