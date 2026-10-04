<!--
  The top of the Forms list (locked list-page format, owner 2026-10-04; docs/design 084447):
  two equal cards with charts. Responses (all forms, last 30 days): count with its change, forms,
  published, all-time responses, and the period's daily bars (↗ opens the inbox). Forms by status:
  the design's thin-line status overview with a legend; a status filters the list.
-->
<script setup lang="ts">
import type { ResponseInsights } from '#shared/types/responses'

const props = defineProps<{ status?: string | null; dots: Record<string, string> }>()
const emit = defineEmits<{ status: [status: string] }>()
const { t } = useI18n()
const api = useApi()
const { number } = useFormat()
const { counts } = useNavCounts()

const insights = ref<ResponseInsights | null>(null)
onMounted(async () => {
  try {
    const to = new Date().toISOString().slice(0, 10)
    const from = new Date(Date.now() - 29 * 86_400_000).toISOString().slice(0, 10)
    insights.value = (await api.get<ResponseInsights>('/responses/insights', { from, to }, { background: true })).data
  } catch {
    insights.value = null
  }
})
const trend = computed(() => {
  const period = insights.value?.period
  return period?.previous ? Math.round(((period.count - period.previous) / period.previous) * 100) : null
})
const forms = computed(() => counts.value?.forms)
const parts = computed(() =>
  (['draft', 'published', 'closed', 'archived'] as const).map(key => ({ key, label: t(`status.${key}`), count: forms.value?.[key] ?? 0, color: props.dots[key]! })),
)
const stats = computed(() => [
  { label: t('forms.overview.forms'), value: number((forms.value?.all ?? 0) + (forms.value?.archived ?? 0)) },
  { label: t('status.published'), value: number(forms.value?.published ?? 0) },
  { label: t('responses.kpi.totalLabel'), value: number(insights.value?.total ?? 0) },
])
</script>

<template>
  <div class="grid gap-4 lg:grid-cols-2">
    <!-- Responses, all forms -->
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <div class="flex flex-col">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('forms.overview.responsesAll') }}</h2>
          <span class="text-xs text-muted">{{ t('forms.overview.last30Short') }}</span>
        </div>
        <UButton to="/responses" icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" square :aria-label="t('nav.responses')" />
      </div>
      <div v-if="insights" class="flex flex-1 items-end gap-5">
        <div class="flex shrink-0 flex-col gap-3">
          <div class="flex items-center gap-2.5">
            <UIcon name="i-lucide-inbox" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(insights.period.count) }}</span>
            <div class="flex flex-col gap-0.5">
              <UBadge v-if="trend !== null" :label="`${trend > 0 ? '+' : ''}${trend}%`" :color="trend >= 0 ? 'success' : 'error'" variant="subtle" size="sm" class="w-fit rounded-md tabular-nums" />
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
        <ChartsMiniBars :days="insights.daily" :label="t('responses.trend.title')" />
      </div>
      <div v-else class="flex flex-1 items-end gap-5">
        <USkeleton class="h-16 w-40" />
        <USkeleton class="hidden h-24 flex-1 sm:block" />
      </div>
    </UCard>

    <!-- Forms by status -->
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('forms.overview.byStatus') }}</h2>
        <span class="text-xs text-muted">{{ t('forms.overview.liveNow', { n: number(forms?.published ?? 0) }) }}</span>
      </div>
      <div v-if="forms" class="flex flex-1 items-end gap-6">
        <ChartsLines :parts="parts" :selected="status" class="min-w-0 flex-1" @pick="key => emit('status', key)" />
        <ul class="hidden shrink-0 flex-col gap-1.5 sm:flex">
          <li v-for="part in parts" :key="part.key">
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-md px-1.5 py-0.5 text-start text-xs hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :class="status === part.key ? 'bg-elevated' : ''"
              :aria-pressed="status === part.key"
              @click="emit('status', part.key)"
            >
              <span class="size-2 shrink-0 rounded-[2px]" :class="part.color" />
              <span class="w-20 truncate text-default">{{ part.label }}</span>
              <span class="ms-auto font-medium text-highlighted tabular-nums">{{ number(part.count) }}</span>
            </button>
          </li>
        </ul>
      </div>
      <USkeleton v-else class="h-24 w-full" />
    </UCard>
  </div>
</template>
