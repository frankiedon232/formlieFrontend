<!--
  The top of a folder's page (F11 M4; locked list format, rule 21): two equal chart cards.
  Responses in the last 30 days (count with its change, forms, published, all time, average
  completion, and daily bars), and the folder's forms by status as the design's thin lines with a
  legend that filters the list below.
-->
<script setup lang="ts">
import type { FolderRow } from '#shared/types/forms'

const props = defineProps<{ folder: FolderRow; status?: string | null; dots: Record<string, string> }>()
const emit = defineEmits<{ status: [status: string] }>()
const { t } = useI18n()
const { number } = useFormat()

const trend = computed(() => (props.folder.previous_30d ? Math.round(((props.folder.responses_30d - props.folder.previous_30d) / props.folder.previous_30d) * 100) : null))
const stats = computed(() => [
  { label: t('forms.overview.forms'), value: number(props.folder.forms_count) },
  { label: t('status.published'), value: number(props.folder.status_counts.published) },
  { label: t('responses.kpi.totalLabel'), value: number(props.folder.responses_count) },
  { label: t('forms.col.completion'), value: props.folder.completion_rate === null ? '–' : `${props.folder.completion_rate}%` },
])
const parts = computed(() =>
  (['draft', 'published', 'closed', 'archived'] as const).map(key => ({ key, label: t(`status.${key}`), count: props.folder.status_counts[key], color: props.dots[key]! })),
)
</script>

<template>
  <div class="grid gap-4 lg:grid-cols-2">
    <!-- Responses, this folder -->
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex flex-col">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('nav.responses') }}</h2>
        <span class="text-xs text-muted">{{ t('forms.overview.last30Short') }}</span>
      </div>
      <div class="flex flex-1 items-end gap-5">
        <div class="flex shrink-0 flex-col gap-3">
          <div class="flex items-center gap-2.5">
            <UIcon name="i-lucide-inbox" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(folder.responses_30d) }}</span>
            <div class="flex flex-col gap-0.5">
              <UBadge v-if="trend !== null" :label="`${trend > 0 ? '+' : ''}${trend}%`" :color="trend >= 0 ? 'success' : 'error'" variant="subtle" size="sm" class="w-fit rounded-md tabular-nums" />
              <span class="text-[11px] text-muted">{{ t('responses.overview.vsBefore') }}</span>
            </div>
          </div>
          <dl class="grid grid-cols-2 gap-x-5 gap-y-2 sm:flex sm:gap-4">
            <div v-for="stat in stats" :key="stat.label" class="flex min-w-0 flex-col">
              <dt class="truncate text-[11px] text-muted">{{ stat.label }}</dt>
              <dd class="truncate text-sm font-medium text-highlighted tabular-nums">{{ stat.value }}</dd>
            </div>
          </dl>
        </div>
        <ChartsMiniBars :days="folder.daily" :label="t('responses.trend.title')" />
      </div>
    </UCard>

    <!-- Forms by status -->
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('forms.overview.byStatus') }}</h2>
        <span class="text-xs text-muted">{{ t('forms.overview.liveNow', { n: number(folder.status_counts.published) }) }}</span>
      </div>
      <div class="flex flex-1 items-end gap-6">
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
    </UCard>
  </div>
</template>
