<!--
  The analytics panel's content: fact tiles; the funnel (opened → started → completed) as slim
  bars; then Pages or Questions (chips in a sliding row): how many reached each, how many left
  there (red when it is the biggest stop), and for questions how many answered and how long it took,
  in two-column tiles of equal height.
-->
<script setup lang="ts">
import type { FormFunnel } from '#shared/types/analytics'

const props = defineProps<{ funnel: FormFunnel }>()
const { t } = useI18n()
const { number } = useFormat()
const { duration } = useResponseFormat()

const totals = computed(() => props.funnel.totals)
const tiles = computed(() => [
  { key: 'views', icon: 'i-lucide-eye', label: t('analytics.views'), value: number(totals.value.views) },
  { key: 'starts', icon: 'i-lucide-pointer', label: t('analytics.started'), value: number(totals.value.starts) },
  { key: 'completions', icon: 'i-lucide-circle-check', label: t('analytics.completedLabel'), value: number(totals.value.completions) },
  { key: 'rate', icon: 'i-lucide-percent', label: t('analytics.rate'), value: `${number(totals.value.completion_rate, { maximumFractionDigits: 1 })}%` },
  { key: 'time', icon: 'i-lucide-timer', label: t('analytics.time'), value: totals.value.median_seconds ? duration(totals.value.median_seconds) : '–' },
  { key: 'left', icon: 'i-lucide-log-out', label: t('analytics.detail.left'), value: number(Math.max(0, totals.value.starts - totals.value.completions)) },
])
const steps = computed(() => [
  { key: 'views', label: t('analytics.views'), value: totals.value.views },
  { key: 'starts', label: t('analytics.started'), value: totals.value.starts },
  { key: 'completions', label: t('analytics.completedLabel'), value: totals.value.completions },
])
const share = (value: number, of: number) => (of ? Math.round((value / of) * 1000) / 10 : 0)

const tab = ref<'pages' | 'questions'>('questions')
const chips = computed(() => [
  { key: 'questions', label: t('analytics.detail.questions'), count: props.funnel.fields.length },
  { key: 'pages', label: t('analytics.detail.pages'), count: props.funnel.pages.length },
])
const worstField = computed(() => Math.max(0, ...props.funnel.fields.map(field => field.left)))
const worstPage = computed(() => Math.max(0, ...props.funnel.pages.map(page => page.left)))
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
      <div v-for="tile in tiles" :key="tile.key" class="flex min-w-0 items-center gap-2.5 rounded-lg border border-default p-2.5">
        <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="tile.icon" class="size-4 text-muted" /></span>
        <div class="flex min-w-0 flex-col">
          <span class="truncate text-[11px] text-muted">{{ tile.label }}</span>
          <span class="truncate text-sm font-semibold text-highlighted tabular-nums">{{ tile.value }}</span>
        </div>
      </div>
    </div>

    <section class="flex flex-col gap-3">
      <h3 class="text-sm font-semibold text-highlighted">{{ t('analytics.detail.funnel') }}</h3>
      <div v-for="(step, i) in steps" :key="step.key" class="flex flex-col gap-1.5">
        <div class="flex items-baseline justify-between gap-3 text-sm">
          <span class="font-medium text-highlighted">{{ step.label }}</span>
          <span class="text-xs text-muted tabular-nums">
            {{ number(step.value) }}<template v-if="i"> · <span class="font-medium text-highlighted">{{ number(share(step.value, steps[i - 1]!.value), { maximumFractionDigits: 1 }) }}%</span> {{ t('analytics.detail.ofPrevious') }}</template>
          </span>
        </div>
        <div class="h-2 overflow-hidden rounded-full bg-elevated"><div class="h-full rounded-full bg-inverted transition-[width] duration-500" :style="{ width: `${share(step.value, steps[0]!.value)}%` }" /></div>
      </div>
    </section>

    <section class="flex flex-col gap-3">
      <div class="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1" role="tablist">
        <UButton
          v-for="chip in chips"
          :key="chip.key"
          role="tab"
          :aria-selected="tab === chip.key"
          :label="chip.label"
          color="neutral"
          :variant="tab === chip.key ? 'solid' : 'outline'"
          size="sm"
          class="shrink-0 rounded-full"
          @click="tab = chip.key as 'pages' | 'questions'"
        >
          <template #trailing><span class="text-xs tabular-nums opacity-70">{{ chip.count }}</span></template>
        </UButton>
      </div>

      <AppEmpty v-if="(tab === 'pages' ? funnel.pages : funnel.fields).length === 0" size="xs" icon="i-lucide-list-checks" :title="t('analytics.detail.noQuestions')" />
      <div v-else-if="tab === 'pages'" class="grid gap-2 sm:grid-cols-2">
        <div v-for="page in funnel.pages" :key="page.index" class="flex h-full flex-col gap-2 rounded-lg border border-default p-3">
          <div class="flex items-center justify-between gap-2">
            <span class="truncate text-sm font-semibold text-highlighted">{{ page.title || t('analytics.focus.page', { n: page.index + 1 }) }}</span>
            <UIcon v-if="page.left && page.left === worstPage" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('analytics.detail.biggestStop')" />
          </div>
          <div class="flex justify-between text-xs text-muted tabular-nums">
            <span>{{ t('analytics.detail.reached', { n: number(page.reached) }) }}</span>
            <span>{{ t('analytics.detail.leftHere', { n: number(page.left) }) }}</span>
          </div>
          <div class="mt-auto h-1.5 overflow-hidden rounded-full bg-elevated"><div class="h-full rounded-full bg-inverted" :style="{ width: `${share(page.reached, totals.starts)}%` }" /></div>
        </div>
      </div>
      <div v-else class="grid gap-2 sm:grid-cols-2">
        <div v-for="field in funnel.fields" :key="field.key" class="flex h-full flex-col gap-2 rounded-lg border border-default p-3">
          <div class="flex items-start justify-between gap-2">
            <div class="flex min-w-0 flex-col">
              <span class="line-clamp-2 text-sm font-semibold text-highlighted">{{ field.label }}</span>
              <span class="text-[11px] text-muted">{{ t('analytics.focus.page', { n: field.page + 1 }) }}<template v-if="field.required"> · {{ t('analytics.detail.required') }}</template> · {{ duration(field.seconds) }}</span>
            </div>
            <UIcon v-if="field.left && field.left === worstField" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('analytics.detail.biggestStop')" />
          </div>
          <div class="mt-auto flex flex-col gap-1.5">
            <div class="flex justify-between text-xs tabular-nums">
              <span class="text-muted">{{ t('analytics.detail.answered', { n: number(share(field.answered, field.reached), { maximumFractionDigits: 0 }) }) }}</span>
              <span :class="field.left === worstField && field.left ? 'font-medium text-error' : 'text-muted'">{{ t('analytics.detail.leftHere', { n: number(field.left) }) }}</span>
            </div>
            <div class="h-1.5 overflow-hidden rounded-full bg-elevated"><div class="h-full rounded-full bg-inverted" :style="{ width: `${share(field.answered, field.reached)}%` }" /></div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
