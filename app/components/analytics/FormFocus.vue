<!--
  One form at a time (F18, the design's "Project Overview"): the number of forms, ‹ form › to step
  through the busiest ones, ↗ to its full analytics; the form's name and numbers, its completion
  rate as the design's thick ink bar, then "Where people stop" as the design's timeline: the
  questions most people left on, each with ↗ to it in the builder.
-->
<script setup lang="ts">
import type { FormAnalyticsRow, FormFunnel } from '#shared/types/analytics'

const props = defineProps<{ forms: FormAnalyticsRow[] | null; total: number; from: string; to: string }>()
const emit = defineEmits<{ open: [id: string] }>()
const { t } = useI18n()
const api = useApi()
const { number } = useFormat()
const { duration } = useResponseFormat()

const index = ref(0)
watch(() => props.forms, () => (index.value = 0))
const form = computed(() => props.forms?.[index.value] ?? null)
const move = (by: number) => props.forms?.length && (index.value = (index.value + by + props.forms.length) % props.forms.length)

const funnel = ref<FormFunnel | null>(null)
const loading = ref(false)
watch(
  () => [form.value?.id, props.from, props.to] as const,
  async ([id]) => {
    if (!id) return
    loading.value = true
    try {
      const data = (await api.get<FormFunnel>(`/analytics/forms/${id}/funnel`, { from: props.from, to: props.to }, { background: true })).data
      if (data.form.id === form.value?.id) funnel.value = data
    } catch {
      funnel.value = null
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
const stops = computed(() => (funnel.value?.form.id === form.value?.id ? [...(funnel.value?.fields ?? [])].filter(field => field.left).sort((a, b) => b.left - a.left).slice(0, 3) : []))
const share = (left: number) => (form.value?.starts ? Math.round((left / form.value.starts) * 1000) / 10 : 0)
</script>

<template>
  <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex items-center justify-between gap-2">
      <div class="flex min-w-0 items-center gap-2">
        <h2 class="text-sm font-semibold whitespace-nowrap text-highlighted">{{ t('analytics.focus.title') }}</h2>
        <UBadge :label="number(total)" color="neutral" variant="soft" size="sm" class="rounded-md tabular-nums" />
      </div>
      <div class="flex shrink-0 items-center gap-1.5">
        <UFieldGroup size="xs">
          <UButton icon="i-lucide-chevron-left" color="neutral" variant="outline" square class="rtl:-scale-x-100" :disabled="!forms || forms.length < 2" :aria-label="t('analytics.focus.previous')" @click="move(-1)" />
          <UButton :label="form?.name ?? '…'" color="neutral" variant="outline" class="max-w-28 sm:max-w-36 lg:max-w-24 2xl:max-w-36" :ui="{ label: 'truncate' }" :disabled="!form" @click="form && emit('open', form.id)" />
          <UButton icon="i-lucide-chevron-right" color="neutral" variant="outline" square class="rtl:-scale-x-100" :disabled="!forms || forms.length < 2" :aria-label="t('analytics.focus.next')" @click="move(1)" />
        </UFieldGroup>
        <UButton v-if="form" icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" square class="rtl:-scale-x-100" :aria-label="t('analytics.focus.details')" @click="emit('open', form.id)" />
      </div>
    </div>

    <div v-if="!forms" class="flex flex-col gap-3"><USkeleton class="h-4 w-24" /><USkeleton class="h-7 w-3/4" /><USkeleton class="h-10 w-full" /><USkeleton class="h-3 w-full" /></div>
    <AppEmpty v-else-if="!form" size="xs" icon="i-lucide-file-chart-column" :title="t('analytics.focus.empty')" :description="t('analytics.focus.emptyDesc')" />
    <template v-else>
      <div class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between gap-2">
          <span class="flex min-w-0 items-center gap-1.5 text-xs text-muted">
            <UIcon name="i-lucide-file-text" class="size-3.5 shrink-0" />
            <span class="truncate">{{ t('analytics.focus.views', { n: number(form.views) }, form.views) }}</span>
          </span>
          <DataStatusBadge :status="form.status" />
        </div>
        <NuxtLink :to="`/forms/${form.id}`" class="truncate text-xl font-semibold text-highlighted hover:underline focus-visible:underline focus-visible:outline-none sm:text-2xl">{{ form.name }}</NuxtLink>
        <p class="line-clamp-2 text-sm text-muted">
          {{ t('analytics.focus.summary', { starts: number(form.starts), completions: number(form.completions) }) }}<template v-if="form.median_seconds"> · {{ t('analytics.focus.time', { time: duration(form.median_seconds) }) }}</template>
        </p>
      </div>

      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between text-sm">
          <span class="text-muted">{{ t('analytics.rate') }}</span>
          <span class="font-semibold text-highlighted tabular-nums">{{ number(form.completion_rate, { maximumFractionDigits: 1 }) }}%</span>
        </div>
        <div class="h-2 overflow-hidden rounded-full bg-elevated" role="progressbar" :aria-valuenow="form.completion_rate" aria-valuemin="0" aria-valuemax="100" :aria-label="t('analytics.rate')">
          <div class="h-full rounded-full bg-inverted transition-[width] duration-500" :style="{ width: `${form.completion_rate}%` }" />
        </div>
      </div>

      <div class="flex flex-col gap-3 border-t border-default pt-4">
        <h3 class="text-sm font-semibold text-highlighted">{{ t('analytics.focus.stops') }}</h3>
        <div v-if="loading && !stops.length" class="flex flex-col gap-3"><USkeleton v-for="n in 2" :key="n" class="h-10 w-full" /></div>
        <p v-else-if="!stops.length" class="text-sm text-muted">{{ t('analytics.focus.noStops') }}</p>
        <ol v-else class="flex flex-col">
          <li v-for="(stop, i) in stops" :key="stop.key" class="relative flex items-start gap-3 pb-3 last:pb-0">
            <span v-if="i < stops.length - 1" class="absolute start-[5px] top-4 bottom-0 border-s border-dashed border-(--ui-border-accented)" aria-hidden="true" />
            <span class="mt-1 size-3 shrink-0 rounded-[3px] border-2" :class="i === 0 ? 'border-(--ui-text-highlighted) bg-inverted' : 'border-(--ui-border-accented) bg-elevated'" aria-hidden="true" />
            <div class="flex min-w-0 flex-1 flex-col">
              <span class="text-xs text-muted">{{ t('analytics.focus.page', { n: stop.page + 1 }) }} · {{ t('analytics.focus.leftShare', { n: number(share(stop.left), { maximumFractionDigits: 1 }) }) }}</span>
              <span class="truncate text-sm font-semibold text-highlighted">{{ stop.label }}</span>
            </div>
            <UButton :label="t('analytics.focus.view')" trailing-icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" :to="`/forms/${form.id}/build`" class="shrink-0" />
          </li>
        </ol>
      </div>
    </template>
  </UCard>
</template>
