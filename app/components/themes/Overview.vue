<!--
  The top of the Themes page (locked list-page format, CLAUDE.md rule 21; owner 2026-10-04): two
  equal cards with charts. Theme use: forms styled with a library theme (and their share of all
  forms), themes, in use, not used, and the three most used themes as slim bars. Themes by kind:
  the design's thin lines for Formalie, saved and created themes; a kind filters the list.
-->
<script setup lang="ts">
import type { ThemeInsights, ThemeSource } from '#shared/types/forms'

const props = defineProps<{ insights: ThemeInsights | null; source?: string | null }>()
const emit = defineEmits<{ source: [source: ThemeSource] }>()
const { t } = useI18n()
const { number, percent } = useFormat()
const library = useThemes()

const total = computed(() =>
  props.insights
    ? props.insights.by_source.system + props.insights.by_source.saved + props.insights.by_source.created
    : 0,
)
const stats = computed(() => [
  { label: t('themes.overview.themes'), value: number(total.value) },
  { label: t('themes.overview.inUse'), value: number(props.insights?.in_use ?? 0) },
  { label: t('themes.overview.unused'), value: number(total.value - (props.insights?.in_use ?? 0)) },
])
const KIND_COLOR: Record<ThemeSource, string> = {
  system: 'bg-inverted',
  saved: 'bg-violet-600',
  created: 'bg-green-500',
}
const parts = computed(() =>
  (['system', 'saved', 'created'] as const).map(key => ({
    key,
    label: t(`themes.source.${key}`),
    count: props.insights?.by_source[key] ?? 0,
    color: KIND_COLOR[key],
  })),
)
</script>

<template>
  <div class="grid gap-4 lg:grid-cols-2">
    <!-- Theme use -->
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <div class="flex flex-col">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('themes.overview.use') }}</h2>
          <span class="text-xs text-muted">{{ t('themes.overview.styledHint') }}</span>
        </div>
        <UButton
          to="/forms"
          icon="i-lucide-arrow-up-right"
          color="neutral"
          variant="outline"
          size="xs"
          square
          :aria-label="t('nav.forms')"
        />
      </div>
      <div v-if="insights" class="flex flex-1 flex-col gap-5 sm:flex-row sm:items-end">
        <div class="flex shrink-0 flex-col gap-3">
          <div class="flex items-center gap-2.5">
            <UIcon name="i-lucide-palette" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{
              number(insights.forms_styled)
            }}</span>
            <div class="flex flex-col gap-0.5">
              <UBadge
                :label="percent(insights.forms_total ? insights.forms_styled / insights.forms_total : 0)"
                color="neutral"
                variant="subtle"
                size="sm"
                class="w-fit rounded-md tabular-nums"
              />
              <span class="text-[11px] text-muted">{{
                t('themes.overview.ofForms', { n: number(insights.forms_total) })
              }}</span>
            </div>
          </div>
          <dl class="flex gap-4">
            <div v-for="stat in stats" :key="stat.label" class="flex min-w-0 flex-col">
              <dt class="truncate text-[11px] text-muted">{{ stat.label }}</dt>
              <dd class="truncate text-sm font-medium text-highlighted tabular-nums">{{ stat.value }}</dd>
            </div>
          </dl>
        </div>
        <div
          v-if="insights.top.length"
          class="flex min-w-0 flex-1 flex-col gap-2.5"
          :aria-label="t('themes.overview.top')"
        >
          <ChartsMeter
            v-for="(item, index) in insights.top"
            :key="item.id"
            :label="library.nameOf(item)"
            :count="item.forms"
            :total="insights.forms_total"
            :strong="index === 0"
          />
        </div>
        <p v-else class="flex-1 text-sm text-muted">{{ t('themes.overview.noUse') }}</p>
      </div>
      <div v-else class="flex flex-1 items-end gap-5">
        <USkeleton class="h-16 w-40" />
        <USkeleton class="hidden h-20 flex-1 sm:block" />
      </div>
    </UCard>

    <!-- Themes by kind -->
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('themes.overview.byKind') }}</h2>
        <span class="text-xs text-muted">{{
          t('themes.overview.inUseNow', { n: number(insights?.in_use ?? 0) })
        }}</span>
      </div>
      <div v-if="insights" class="flex flex-1 items-end gap-6">
        <ChartsLines
          :parts="parts"
          :selected="source"
          class="min-w-0 flex-1"
          @pick="key => emit('source', key as ThemeSource)"
        />
        <ul class="hidden shrink-0 flex-col gap-1.5 sm:flex">
          <li v-for="part in parts" :key="part.key">
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-md px-1.5 py-0.5 text-start text-xs hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :class="source === part.key ? 'bg-elevated' : ''"
              :aria-pressed="source === part.key"
              @click="emit('source', part.key)"
            >
              <span class="size-2 shrink-0 rounded-[2px]" :class="part.color" />
              <span class="w-28 truncate text-default">{{ part.label }}</span>
              <span class="ms-auto font-medium text-highlighted tabular-nums">{{ number(part.count) }}</span>
            </button>
          </li>
        </ul>
      </div>
      <USkeleton v-else class="h-24 w-full" />
    </UCard>
  </div>
</template>
