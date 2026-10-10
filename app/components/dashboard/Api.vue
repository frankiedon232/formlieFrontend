<!--
  Dashboard → API service view (F21 M4): the API service at work, for people with API service access. KPI
  cards (calls, success rate, response time, errors, webhook deliveries); calls over time (calls and the ones
  that went through) beside the busiest endpoints; then answers by kind (2xx, 4xx, 5xx), the tokens in use,
  webhooks, and the latest failed calls.
-->
<script setup lang="ts">
import type { ApiDashboard, DashboardGroup } from '#shared/types/dashboard'

const props = defineProps<{ from: string; to: string; group?: DashboardGroup }>()
const emit = defineEmits<{ loaded: [group: DashboardGroup] }>()
const { t, d } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { number, relative } = useFormat()

const data = ref<ApiDashboard | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    data.value = (
      await api.get<ApiDashboard>('/dashboard/api', { from: props.from, to: props.to, group: props.group })
    ).data
    emit('loaded', data.value.group)
  } catch (error) {
    failed.value = true
    handle(error)
  }
}
watch(() => [props.from, props.to, props.group], load, { immediate: true })
defineExpose({ refresh: load })

const change = (kpi: { value: number; previous: number | null } | undefined) =>
  kpi && kpi.previous ? Math.round(((kpi.value - kpi.previous) / kpi.previous) * 100) : null
const ms = (n: number) => (n ? `${number(n)} ms` : '–')
const kpis = computed(() => {
  const k = data.value?.kpis
  return [
    {
      key: 'calls',
      icon: 'i-lucide-code-xml',
      label: t('dashboard.apiView.calls'),
      value: k ? number(k.calls.value) : null,
      change: change(k?.calls),
      to: '/api-service/logs',
    },
    {
      key: 'success',
      icon: 'i-lucide-circle-check',
      label: t('dashboard.apiView.success'),
      value: k ? `${number(k.success_rate.value, { maximumFractionDigits: 1 })}%` : null,
      change: null,
      to: '/api-service/analytics',
    },
    {
      key: 'latency',
      icon: 'i-lucide-timer',
      label: t('dashboard.apiView.latency'),
      value: k ? ms(k.latency.value) : null,
      change: change(k?.latency),
      to: '/api-service/analytics',
      lower: true,
    },
    {
      key: 'errors',
      icon: 'i-lucide-circle-x',
      label: t('dashboard.apiView.errors'),
      value: k ? number(k.errors.value) : null,
      change: change(k?.errors),
      to: '/api-service/logs',
      lower: true,
    },
    {
      key: 'deliveries',
      icon: 'i-lucide-webhook',
      label: t('dashboard.apiView.deliveries'),
      value: k ? number(k.deliveries.value) : null,
      change: change(k?.deliveries),
      to: '/api-service/webhooks',
    },
  ]
})

const bucketLabel = (start: string) => {
  const day = new Date(`${start}T00:00:00Z`)
  const group = data.value?.group ?? 'day'
  return group === 'year'
    ? String(day.getUTCFullYear())
    : group === 'month'
      ? d(day, { month: 'short', year: '2-digit', timeZone: 'UTC' })
      : d(day, { day: 'numeric', month: 'short', timeZone: 'UTC' })
}
const active = ref<number | null>(null)
const points = computed(
  () =>
    data.value?.series.map(item => ({
      label: bucketLabel(item.start),
      upper: item.calls,
      lower: item.calls - item.errors,
    })) ?? [],
)
const anyCalls = computed(() => !!data.value?.kpis.calls.value)
const statusTotal = computed(() =>
  data.value ? data.value.statuses.ok + data.value.statuses.client + data.value.statuses.server : 0,
)
const hookTotal = computed(() =>
  data.value ? data.value.webhooks.delivered + data.value.webhooks.failed : 0,
)
const hookCount = computed(() =>
  data.value ? data.value.webhooks.active + data.value.webhooks.failing + data.value.webhooks.paused : 0,
)
</script>

<template>
  <AppEmpty
    v-if="failed && !data"
    icon="i-lucide-cloud-off"
    :title="t('dashboard.failed')"
    :actions="[
      {
        label: t('common.retry'),
        icon: 'i-lucide-refresh-cw',
        color: 'neutral',
        variant: 'outline',
        onClick: load,
      },
    ]"
  />
  <div v-else class="flex flex-col gap-4" :class="data && failed ? 'opacity-60' : ''">
    <div
      class="flex shrink-0 snap-x gap-3 overflow-x-auto [scrollbar-width:none] sm:grid sm:grid-cols-3 sm:overflow-visible xl:grid-cols-5"
    >
      <ChartsKpi
        v-for="kpi in kpis"
        :key="kpi.key"
        class="min-w-[13.5rem] snap-start sm:min-w-0"
        :label="kpi.label"
        :icon="kpi.icon"
        :value="kpi.value"
        :change="kpi.change"
        :to="kpi.to"
        :lower-is-better="!!kpi.lower"
      />
    </div>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <UCard
        variant="outline"
        class="min-w-0 lg:col-span-2"
        :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }"
      >
        <div class="flex flex-col gap-1">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.apiView.traffic') }}</h2>
          <span v-if="data" class="flex items-center gap-2 border-s-2 border-default ps-3">
            <span class="text-2xl font-semibold text-highlighted tabular-nums">{{
              t('dashboard.apiView.callsCount', { n: number(data.kpis.calls.value) }, data.kpis.calls.value)
            }}</span>
            <UBadge
              v-if="change(data.kpis.calls) !== null"
              :label="`${change(data.kpis.calls)! >= 0 ? '+' : ''}${change(data.kpis.calls)}%`"
              :color="change(data.kpis.calls)! >= 0 ? 'success' : 'error'"
              variant="subtle"
              size="sm"
            />
          </span>
          <USkeleton v-else class="h-9 w-48" />
        </div>
        <USkeleton v-if="!data" class="h-64 w-full" />
        <AppEmpty
          v-else-if="!anyCalls"
          size="sm"
          icon="i-lucide-code-xml"
          :title="t('dashboard.apiView.noCalls')"
          :description="t('dashboard.apiView.noCallsDesc')"
          :actions="[
            {
              label: t('dashboard.apiView.openDocs'),
              icon: 'i-lucide-book-open',
              color: 'neutral',
              variant: 'outline',
              to: '/api-service/docs',
            },
          ]"
        />
        <ChartsFlow
          v-else
          v-model:active="active"
          :points="points"
          :upper-label="t('dashboard.apiView.calls')"
          :lower-label="t('dashboard.apiView.through')"
        >
          <template #tooltip="{ index }">
            <p class="truncate text-xs text-muted">{{ points[index]?.label }}</p>
            <div class="mt-2 grid grid-cols-2 gap-x-6 gap-y-2 text-xs">
              <span class="flex flex-col"
                ><span class="text-muted">{{ t('dashboard.apiView.calls') }}</span
                ><span class="text-base font-semibold text-highlighted tabular-nums">{{
                  number(data?.series[index]?.calls ?? 0)
                }}</span></span
              >
              <span class="flex flex-col"
                ><span class="text-muted">{{ t('dashboard.apiView.errors') }}</span
                ><span class="text-base font-semibold text-highlighted tabular-nums">{{
                  number(data?.series[index]?.errors ?? 0)
                }}</span></span
              >
            </div>
          </template>
        </ChartsFlow>
      </UCard>

      <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
        <div class="flex items-center gap-2">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.apiView.endpoints') }}</h2>
          <UButton
            icon="i-lucide-arrow-up-right"
            color="neutral"
            variant="outline"
            size="xs"
            square
            class="ms-auto"
            to="/api-service/endpoints"
            :aria-label="t('dashboard.apiView.endpoints')"
          />
        </div>
        <div v-if="!data" class="flex flex-col gap-2">
          <USkeleton v-for="n in 5" :key="n" class="h-10 w-full" />
        </div>
        <p v-else-if="!data.endpoints.length" class="text-xs text-muted">
          {{ t('dashboard.apiView.noEndpoints') }}
        </p>
        <ul v-else class="flex flex-col divide-y divide-default">
          <li v-for="item in data.endpoints" :key="item.id">
            <NuxtLink
              :to="`/api-service/endpoints/${item.id}`"
              class="flex items-center gap-3 py-2 hover:text-highlighted focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
            >
              <span class="flex min-w-0 flex-1 flex-col">
                <span class="truncate text-sm text-highlighted">{{ item.name }}</span>
                <span class="truncate text-[11px] text-muted"
                  ><template v-if="item.service">{{ item.service }} · </template
                  >{{ ms(item.latency_ms) }}</span
                >
              </span>
              <span class="flex flex-col items-end">
                <span class="text-sm font-medium text-highlighted tabular-nums">{{
                  number(item.calls)
                }}</span>
                <span v-if="item.errors" class="text-[11px] text-error tabular-nums">{{
                  t('dashboard.apiView.errorsCount', { n: number(item.errors) }, item.errors)
                }}</span>
              </span>
            </NuxtLink>
          </li>
        </ul>
      </UCard>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.apiView.answers') }}</h2>
        <div v-if="!data" class="flex flex-col gap-3">
          <USkeleton v-for="n in 3" :key="n" class="h-7 w-full" />
        </div>
        <p v-else-if="!statusTotal" class="text-xs text-muted">{{ t('dashboard.apiView.noCalls') }}</p>
        <template v-else>
          <ChartsMeter
            :label="t('dashboard.apiView.ok')"
            icon="i-lucide-circle-check"
            :count="data.statuses.ok"
            :total="statusTotal"
            strong
          />
          <ChartsMeter
            :label="t('dashboard.apiView.client')"
            icon="i-lucide-circle-alert"
            :count="data.statuses.client"
            :total="statusTotal"
          />
          <ChartsMeter
            :label="t('dashboard.apiView.server')"
            icon="i-lucide-server-crash"
            :count="data.statuses.server"
            :total="statusTotal"
          />
        </template>
      </UCard>

      <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
        <div class="flex items-center gap-2">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.apiView.tokens') }}</h2>
          <UButton
            icon="i-lucide-arrow-up-right"
            color="neutral"
            variant="outline"
            size="xs"
            square
            class="ms-auto"
            to="/api-service/access"
            :aria-label="t('dashboard.apiView.tokens')"
          />
        </div>
        <div v-if="!data" class="flex flex-col gap-2">
          <USkeleton v-for="n in 4" :key="n" class="h-9 w-full" />
        </div>
        <p v-else-if="!data.tokens.length" class="text-xs text-muted">
          {{ t('dashboard.apiView.noTokens') }}
        </p>
        <ul v-else class="flex flex-col divide-y divide-default">
          <li v-for="item in data.tokens" :key="item.id" class="flex items-center gap-2 py-1.5">
            <span class="flex min-w-0 flex-1 flex-col">
              <span class="truncate text-sm text-highlighted">{{ item.name }}</span>
              <span class="truncate text-[11px] text-muted">{{
                item.last_used_at
                  ? t('dashboard.apiView.used', { when: relative(item.last_used_at) })
                  : t('dashboard.apiView.neverUsed')
              }}</span>
            </span>
            <UBadge :label="item.mode" color="neutral" variant="outline" size="sm" />
            <span class="text-sm font-medium text-highlighted tabular-nums">{{ number(item.calls) }}</span>
          </li>
        </ul>
      </UCard>

      <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
        <div class="flex items-center gap-2">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.apiView.webhooks') }}</h2>
          <UButton
            icon="i-lucide-arrow-up-right"
            color="neutral"
            variant="outline"
            size="xs"
            square
            class="ms-auto"
            to="/api-service/webhooks"
            :aria-label="t('dashboard.apiView.webhooks')"
          />
        </div>
        <div v-if="!data" class="flex flex-col gap-3">
          <USkeleton v-for="n in 3" :key="n" class="h-7 w-full" />
        </div>
        <p v-else-if="!hookCount" class="text-xs text-muted">{{ t('dashboard.apiView.noWebhooks') }}</p>
        <template v-else>
          <div class="flex flex-wrap gap-1.5">
            <UBadge
              :label="t('dashboard.apiView.hooksActive', { n: number(data.webhooks.active) })"
              color="neutral"
              variant="outline"
              size="sm"
            />
            <UBadge
              v-if="data.webhooks.failing"
              :label="t('dashboard.apiView.hooksFailing', { n: number(data.webhooks.failing) })"
              color="error"
              variant="subtle"
              size="sm"
            />
            <UBadge
              v-if="data.webhooks.paused"
              :label="t('dashboard.apiView.hooksPaused', { n: number(data.webhooks.paused) })"
              color="neutral"
              variant="subtle"
              size="sm"
            />
          </div>
          <ChartsMeter
            :label="t('dashboard.apiView.delivered')"
            icon="i-lucide-circle-check"
            :count="data.webhooks.delivered"
            :total="hookTotal"
            strong
          />
          <ChartsMeter
            :label="t('dashboard.apiView.notDelivered')"
            icon="i-lucide-circle-x"
            :count="data.webhooks.failed"
            :total="hookTotal"
          />
        </template>
      </UCard>

      <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
        <div class="flex items-center gap-2">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.apiView.failedCalls') }}</h2>
          <UButton
            icon="i-lucide-arrow-up-right"
            color="neutral"
            variant="outline"
            size="xs"
            square
            class="ms-auto"
            to="/api-service/logs"
            :aria-label="t('dashboard.apiView.failedCalls')"
          />
        </div>
        <div v-if="!data" class="flex flex-col gap-2">
          <USkeleton v-for="n in 4" :key="n" class="h-9 w-full" />
        </div>
        <p v-else-if="!data.errors.length" class="text-xs text-muted">
          {{ t('dashboard.apiView.noFailed') }}
        </p>
        <ul v-else class="flex flex-col divide-y divide-default">
          <li v-for="item in data.errors" :key="item.id" class="flex items-center gap-2 py-1.5">
            <span class="flex min-w-0 flex-1 flex-col">
              <span class="truncate font-mono text-xs text-highlighted"
                >{{ item.method }} {{ item.path }}</span
              >
              <span class="truncate text-[11px] text-muted"
                ><template v-if="item.code">{{ item.code }} · </template>{{ relative(item.at) }}</span
              >
            </span>
            <UBadge
              :label="String(item.status)"
              :color="item.status >= 500 ? 'error' : 'warning'"
              variant="subtle"
              size="sm"
            />
          </li>
        </ul>
      </UCard>
    </div>
  </div>
</template>
