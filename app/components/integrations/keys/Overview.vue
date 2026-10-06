<!--
  Top of API service → API keys (locked list format, rule 21): two equal chart cards. Calls with
  API keys in the last 30 days (with the change, keys / active / unused for 90 days, daily bars),
  and keys by status as thin lines whose legend filters the list.
-->
<script setup lang="ts">
import type { ApiKeyInsights, ApiKeyStatus } from '#shared/types/integrations'

const props = defineProps<{ insights: ApiKeyInsights | null; status?: string | null }>()
const emit = defineEmits<{ status: [status: string] }>()
const { t } = useI18n()
const { number } = useFormat()
const trend = computed(() => (props.insights?.previous_30d ? Math.round(((props.insights.calls_30d - props.insights.previous_30d) / props.insights.previous_30d) * 100) : null))
const stats = computed(() =>
  props.insights
    ? [
        { label: t('integrations.keys.kpi.keys'), value: number(props.insights.total) },
        { label: t('status.active'), value: number(props.insights.by_status.active) },
        { label: t('integrations.keys.kpi.unused'), value: number(props.insights.unused_90d) },
      ]
    : [],
)
const COLORS: Record<ApiKeyStatus, string> = { active: 'bg-(--ui-text-highlighted)', expiring: 'bg-amber-500', expired: 'bg-violet-500', revoked: 'bg-red-500' }
const parts = computed(() => (['active', 'expiring', 'expired', 'revoked'] as const).map(key => ({ key, label: t(`status.${key}`), count: props.insights?.by_status[key] ?? 0, color: COLORS[key] })))
</script>

<template>
  <div class="grid shrink-0 gap-4 lg:grid-cols-2">
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex flex-col">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('integrations.keys.kpi.calls') }}</h2>
        <span class="text-xs text-muted">{{ t('forms.overview.last30Short') }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-5"><USkeleton class="h-16 w-48" /><USkeleton class="h-24 flex-1" /></div>
      <div v-else class="flex flex-1 items-end gap-5">
        <div class="flex shrink-0 flex-col gap-3">
          <div class="flex items-center gap-2.5">
            <UIcon name="i-lucide-arrow-left-right" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(insights.calls_30d) }}</span>
            <div class="flex flex-col gap-0.5">
              <UBadge v-if="trend !== null" :label="`${trend > 0 ? '+' : ''}${trend}%`" color="neutral" variant="subtle" size="sm" class="w-fit rounded-md tabular-nums" />
              <span class="text-[11px] text-muted">{{ t('responses.overview.vsBefore') }}</span>
            </div>
          </div>
          <dl class="flex gap-4">
            <div v-for="stat in stats" :key="stat.label" class="flex min-w-0 flex-col">
              <dt class="truncate text-[11px] text-muted">{{ stat.label }}</dt>
              <dd class="truncate text-sm font-medium text-highlighted tabular-nums">{{ stat.value }}</dd>
            </div>
          </dl>
        </div>
        <ChartsMiniBars :days="insights.daily" :label="t('integrations.keys.kpi.calls')" />
      </div>
    </UCard>

    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('integrations.keys.kpi.byStatus') }}</h2>
        <span class="text-xs text-muted">{{ t('integrations.keys.kpi.expiringHint') }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-6"><USkeleton class="h-24 flex-1" /></div>
      <AppEmpty v-else-if="!insights.total" size="xs" icon="i-lucide-key" :title="t('integrations.keys.empty')" />
      <div v-else class="flex flex-1 items-end gap-6">
        <ChartsLines :parts="parts" :selected="status" class="min-w-0 flex-1" @pick="key => emit('status', key)" />
        <ul class="hidden shrink-0 flex-col gap-1 sm:flex">
          <li v-for="part in parts" :key="part.key">
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-md px-1.5 py-0.5 text-start text-xs hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :class="status === part.key ? 'bg-elevated' : ''"
              :aria-pressed="status === part.key"
              @click="emit('status', part.key)"
            >
              <span class="size-2 shrink-0 rounded-[2px]" :class="part.color" />
              <span class="w-24 truncate text-default">{{ part.label }}</span>
              <span class="ms-auto font-medium text-highlighted tabular-nums">{{ number(part.count) }}</span>
            </button>
          </li>
        </ul>
      </div>
    </UCard>
  </div>
</template>
