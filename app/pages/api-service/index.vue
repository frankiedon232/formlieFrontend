<!--
  API service overview (own rail area, F13; the design's dashboard, docs/design 092034): five KPI
  cards (services, endpoints, calls, error share, tokens), traffic beside one endpoint at a time,
  recent calls, then the three ways a form collects data (link, embed, API) with an example address,
  and every section one click away. The F21 dashboards come later and may reuse these pieces.
-->
<script setup lang="ts">
import type { ApiAnalytics, ApiInsights, ApiTokenInsights } from '#shared/types/apiService'
import { API_METHODS, apiEndpointUrl } from '#shared/utils/urls/public'

definePageMeta({ breadcrumb: 'nav.apiService' })
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { number, percent } = useFormat()
const config = useRuntimeConfig().public
// Guided setup (owner, 2026-10-06): the five steps until an endpoint is live with a live token
const setup = useApiSetup()
onMounted(() => void setup.refresh())
const setupDone = computed(() => { const s = setup.summary.value; return !!s && s.services > 0 && s.endpoints > 0 && s.endpoints_live > 0 && s.tokens_live > 0 })
const setupCount = computed(() => { const s = setup.summary.value; return s ? [s.services > 0, s.endpoints > 0, s.tokens_live + s.tokens_test > 0, s.endpoints_live > 0 && s.tokens_live > 0].filter(Boolean).length : 0 })
useHead({ title: () => t('nav.apiService') })
const { can } = useCan()

const analytics = ref<ApiAnalytics | null>(null)
const services = ref<ApiInsights | null>(null)
const endpoints = ref<ApiInsights | null>(null)
const tokens = ref<ApiTokenInsights | null>(null)
onMounted(async () => {
  try {
    const [a, b, c, d] = await Promise.all([
      api.get<ApiAnalytics>('/api-analytics', { period: '30d' }),
      api.get<ApiInsights>('/api-services/insights'),
      api.get<ApiInsights>('/api-endpoints/insights'),
      api.get<ApiTokenInsights>('/api-tokens/insights'),
    ])
    analytics.value = a.data
    services.value = b.data
    endpoints.value = c.data
    tokens.value = d.data
  } catch (error) {
    handle(error)
  }
})
const change = (now?: number, before?: number) => (now != null && before ? Math.round(((now - before) / before) * 100) : null)
const kpis = computed(() => {
  const a = analytics.value
  return [
    { key: 'services', icon: 'i-lucide-boxes', label: t('nav.apiServices'), value: services.value ? number(services.value.total) : null, hint: services.value ? t('apiService.kpi.active', { n: number(services.value.by_status.active) }) : '', to: '/api-service/services' },
    { key: 'endpoints', icon: 'i-lucide-route', label: t('nav.apiEndpoints'), value: endpoints.value ? number(endpoints.value.total) : null, hint: endpoints.value ? t('apiService.home.answering', { n: number(endpoints.value.by_status.active) }) : '', to: '/api-service/endpoints' },
    { key: 'calls', icon: 'i-lucide-arrow-left-right', label: t('apiService.kpi.calls'), value: a ? number(a.totals.calls) : null, change: change(a?.totals.calls, a?.previous.calls), to: '/api-service/analytics' },
    { key: 'errors', icon: 'i-lucide-octagon-alert', label: t('apiService.analytics.errorShare'), value: a ? percent(a.totals.calls ? a.totals.errors / a.totals.calls : 0, 1) : null, hint: t('apiService.home.last30'), to: { path: '/api-service/logs', query: { class: '4xx,5xx' } } },
    { key: 'tokens', icon: 'i-lucide-key-round', label: t('apiService.tokens.title'), value: tokens.value ? number(tokens.value.by_status.active + tokens.value.by_status.expiring) : null, hint: tokens.value ? t('apiService.home.tokensHint', { n: number(tokens.value.by_mode.test) }) : '', to: '/api-service/auth' },
  ]
})
const example = apiEndpointUrl(config.apiServiceUrl, 'k7Qm2xP9aZ', 'register-account')
const channels = [
  { key: 'link', icon: 'i-lucide-link' },
  { key: 'embed', icon: 'i-lucide-code' },
  { key: 'api', icon: 'i-lucide-code-xml' },
]
const shortcuts = [
  { key: 'auth', nav: 'apiAuth', icon: 'i-lucide-key-round', to: '/api-service/auth' },
  { key: 'access', nav: 'apiAccess', icon: 'i-lucide-shield-check', to: '/api-service/access' },
  { key: 'logs', nav: 'apiLogs', icon: 'i-lucide-scroll-text', to: '/api-service/logs' },
  { key: 'docs', nav: 'apiDocs', icon: 'i-lucide-book-open', to: '/api-service/docs' },
]
</script>

<template>
  <AppPanel id="api-service" :title="t('nav.apiService')" :subtitle="t('apiService.subtitle')" subtitle-icon="i-lucide-code-xml">
    <template #actions>
      <UButton v-if="can('api.tokens')" :label="t('apiService.tokens.newTitle')" icon="i-lucide-key-round" color="neutral" variant="outline" to="/api-service/auth" data-help="api-tokens" class="hidden sm:inline-flex" />
      <UButton v-if="can('api.endpoints')" :label="t('apiService.actions.newEndpoint')" icon="i-lucide-plus" color="neutral" to="/api-service/endpoints/new" data-help="api-new-endpoint" />
    </template>

    <UCard v-if="setup.summary.value && !setupDone" variant="outline" class="shrink-0" data-help="api-setup" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex flex-wrap items-start justify-between gap-2">
        <div class="flex flex-col gap-0.5">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.journey.title') }}</h2>
          <p class="text-xs text-muted">{{ t('apiService.journey.text') }}</p>
        </div>
        <UBadge :label="t('apiService.journey.progress', { n: setupCount, total: 4 })" color="neutral" variant="subtle" class="rounded-md tabular-nums" />
      </div>
      <ApiJourney :summary="setup.summary.value" />
    </UCard>

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
        :lower-is-better="kpi.key === 'errors'"
        :to="kpi.to"
      />
    </div>

    <div class="grid shrink-0 gap-4 lg:grid-cols-3">
      <ApiAnalyticsTraffic class="lg:col-span-2" :analytics="analytics" :change="change(analytics?.totals.calls, analytics?.previous.calls)" />
      <ApiAnalyticsEndpointFocus :analytics="analytics" />
    </div>

    <ApiRecentCalls class="shrink-0" />

    <div class="grid shrink-0 gap-4 lg:grid-cols-3">
      <UCard variant="outline" class="lg:col-span-2" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-5' }">
        <div>
          <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.channels.title') }}</h2>
          <p class="text-xs text-muted">{{ t('apiService.channels.hint') }}</p>
        </div>
        <div class="grid gap-2 sm:grid-cols-3">
          <div v-for="channel in channels" :key="channel.key" class="flex items-center gap-2.5 rounded-lg border p-2.5" :class="channel.key === 'api' ? 'border-(--ui-border-inverted)' : 'border-default'">
            <span class="flex size-8 shrink-0 items-center justify-center rounded-md" :class="channel.key === 'api' ? 'bg-inverted text-inverted' : 'border border-default'"><UIcon :name="channel.icon" class="size-4" /></span>
            <span class="truncate text-sm font-medium text-highlighted">{{ t(`apiService.channels.${channel.key}`) }}</span>
          </div>
        </div>
        <div class="flex flex-col gap-1.5">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="text-xs text-muted">{{ t('apiService.example') }}</span>
            <ApiMethods :methods="[...API_METHODS]" size="xs" />
          </div>
          <code class="block overflow-x-auto rounded-md bg-elevated px-3 py-2 font-mono text-sm text-highlighted" dir="ltr">{{ example }}</code>
        </div>
      </UCard>
      <UCard variant="outline" :ui="{ body: 'flex flex-col gap-2 p-4 sm:p-5' }">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.home.shortcuts') }}</h2>
        <NuxtLink v-for="item in shortcuts" :key="item.key" :to="item.to" class="group flex items-center gap-3 rounded-lg p-2 transition-colors hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
          <span class="flex size-8 shrink-0 items-center justify-center rounded-md border border-default"><UIcon :name="item.icon" class="size-4 text-highlighted" /></span>
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="truncate text-sm font-medium text-highlighted">{{ t(`nav.${item.nav}`) }}</span>
            <span class="truncate text-xs text-muted">{{ t(`apiService.section.${item.key}`) }}</span>
          </span>
          <UIcon name="i-lucide-arrow-up-right" class="size-4 shrink-0 text-muted group-hover:text-highlighted rtl:-scale-x-100" />
        </NuxtLink>
      </UCard>
    </div>
  </AppPanel>
</template>
