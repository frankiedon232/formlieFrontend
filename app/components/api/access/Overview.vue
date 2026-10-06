<!--
  Top of API service → Access rules (locked list format, rule 21): two equal chart cards. Calls
  refused by rules in the last 30 days (with the change, rules / allow / block and how many hit a
  rate limit, daily bars), and rules by kind as thin lines whose legend filters the list.
-->
<script setup lang="ts">
import { API_RULE_KINDS, type ApiAccessInsights } from '#shared/types/apiService'

const props = defineProps<{ insights: ApiAccessInsights | null; kind?: string | null }>()
const emit = defineEmits<{ kind: [kind: string] }>()
const { t } = useI18n()
const { number } = useFormat()
const trend = computed(() => (props.insights?.previous_30d ? Math.round(((props.insights.refused_30d - props.insights.previous_30d) / props.insights.previous_30d) * 100) : null))
const stats = computed(() =>
  props.insights
    ? [
        { label: t('apiService.access.kpi.rules'), value: number(props.insights.total) },
        { label: t('apiService.access.action.allow'), value: number(props.insights.by_action.allow) },
        { label: t('apiService.access.action.block'), value: number(props.insights.by_action.block) },
        { label: t('apiService.access.kpi.limited'), value: number(props.insights.limited_30d) },
      ]
    : [],
)
const COLORS = { ip: 'bg-(--ui-text-highlighted)', domain: 'bg-violet-500', country: 'bg-amber-500', region: 'bg-green-500' } as const
const parts = computed(() => API_RULE_KINDS.map(key => ({ key, label: t(`apiService.access.kind.${key}`), count: props.insights?.by_kind[key] ?? 0, color: COLORS[key] })))
</script>

<template>
  <div class="grid shrink-0 gap-4 lg:grid-cols-2">
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex flex-col">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.access.kpi.refused') }}</h2>
        <span class="text-xs text-muted">{{ t('forms.overview.last30Short') }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-5"><USkeleton class="h-16 w-48" /><USkeleton class="h-24 flex-1" /></div>
      <div v-else class="flex flex-1 items-end gap-5">
        <div class="flex shrink-0 flex-col gap-3">
          <div class="flex items-center gap-2.5">
            <UIcon name="i-lucide-shield-x" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(insights.refused_30d) }}</span>
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
        <ChartsMiniBars :days="insights.daily" :label="t('apiService.access.kpi.refused')" />
      </div>
    </UCard>

    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.access.kpi.byKind') }}</h2>
        <span class="text-xs text-muted">{{ t('apiService.access.kpi.blockWins') }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-6"><USkeleton class="h-24 flex-1" /></div>
      <AppEmpty v-else-if="!insights.total" size="xs" icon="i-lucide-shield" :title="t('apiService.access.empty')" />
      <div v-else class="flex flex-1 items-end gap-6">
        <ChartsLines :parts="parts" :selected="kind" class="min-w-0 flex-1" @pick="key => emit('kind', key)" />
        <ul class="hidden shrink-0 flex-col gap-1 sm:flex">
          <li v-for="part in parts" :key="part.key">
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-md px-1.5 py-0.5 text-start text-xs hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :class="kind === part.key ? 'bg-elevated' : ''"
              :aria-pressed="kind === part.key"
              @click="emit('kind', part.key)"
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
