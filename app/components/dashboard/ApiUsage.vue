<!--
  Dashboard → API service view, lower row (F21 M4): answers by kind (2xx, 4xx, 5xx), the tokens in use with their
  calls and last use, webhooks (active, failing, paused; delivered or not) and the latest failed calls.
-->
<script setup lang="ts">
import type { ApiDashboard } from '#shared/types/dashboard'

const props = defineProps<{ data: ApiDashboard | null }>()
const { t } = useI18n()
const { number, relative } = useFormat()

const statusTotal = computed(() =>
  props.data ? props.data.statuses.ok + props.data.statuses.client + props.data.statuses.server : 0,
)
const hookTotal = computed(() =>
  props.data ? props.data.webhooks.delivered + props.data.webhooks.failed : 0,
)
const hookCount = computed(() =>
  props.data ? props.data.webhooks.active + props.data.webhooks.failing + props.data.webhooks.paused : 0,
)
</script>

<template>
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
            <span class="truncate font-mono text-xs text-highlighted">{{ item.method }} {{ item.path }}</span>
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
</template>
