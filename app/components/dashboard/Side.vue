<!--
  Dashboard → side card (F21, the design's "Project Overview" + "Work Timeline"): the busiest forms one at a time
  (‹ › to move, ↗ to open) with their responses, change, completion bar and how many wait for review; below,
  what is coming up (forms opening or closing, the renewal, a plan change) with View.
-->
<script setup lang="ts">
import type { WorkspaceDashboard } from '#shared/types/dashboard'

const props = defineProps<{ data: WorkspaceDashboard | null }>()
const { t } = useI18n()
const { number, date } = useFormat()

const at = ref(0)
watch(() => props.data, () => (at.value = 0))
const forms = computed(() => props.data?.top_forms ?? [])
const form = computed(() => forms.value[at.value] ?? null)
const change = computed(() => (form.value?.previous ? Math.round(((form.value.responses - form.value.previous) / form.value.previous) * 100) : null))
const move = (step: number) => forms.value.length && (at.value = (at.value + step + forms.value.length) % forms.value.length)
const ICON = { opens: 'i-lucide-calendar-plus', closes: 'i-lucide-calendar-x', renews: 'i-lucide-repeat', plan_change: 'i-lucide-arrow-up-down', card_expires: 'i-lucide-credit-card' } as const
</script>

<template>
  <UCard variant="outline" class="flex h-full min-w-0 flex-col" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex items-center gap-2">
      <h2 class="text-sm font-semibold whitespace-nowrap text-highlighted">{{ t('dashboard.forms.title') }}</h2>
      <UBadge v-if="forms.length" :label="String(forms.length)" color="neutral" variant="outline" size="sm" />
      <span class="ms-auto flex items-center gap-1">
        <UButton icon="i-lucide-chevron-left" color="neutral" variant="outline" size="xs" square class="rtl:rotate-180" :disabled="forms.length < 2" :aria-label="t('dashboard.forms.previous')" @click="move(-1)" />
        <span class="hidden max-w-24 truncate rounded-md border border-default px-2 py-0.5 text-xs text-default sm:inline">{{ form?.name ?? '–' }}</span>
        <UButton icon="i-lucide-chevron-right" color="neutral" variant="outline" size="xs" square class="rtl:rotate-180" :disabled="forms.length < 2" :aria-label="t('dashboard.forms.next')" @click="move(1)" />
        <UButton v-if="form" icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" square :to="`/forms/${form.id}`" :aria-label="t('dashboard.forms.open')" />
      </span>
    </div>

    <USkeleton v-if="!data" class="h-36 w-full" />
    <AppEmpty v-else-if="!form" size="xs" icon="i-lucide-file-text" :title="t('dashboard.forms.none')" :actions="[{ label: t('dashboard.newForm'), icon: 'i-lucide-plus', color: 'neutral', variant: 'outline', to: '/forms/new' }]" />
    <div v-else class="flex flex-col gap-3">
      <div class="flex items-center gap-2">
        <span class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-inbox" class="size-3.5" />{{ t('dashboard.forms.responses', { n: number(form.responses) }, form.responses) }}</span>
        <UBadge v-if="change !== null" :label="`${change >= 0 ? '+' : ''}${change}%`" :color="change >= 0 ? 'success' : 'error'" variant="subtle" size="sm" />
        <DataStatusBadge :status="form.status" class="ms-auto" />
      </div>
      <NuxtLink :to="`/forms/${form.id}`" class="truncate text-xl font-semibold text-highlighted hover:underline">{{ form.name }}</NuxtLink>
      <p class="text-xs text-muted">{{ form.to_review ? t('dashboard.forms.toReview', { n: number(form.to_review) }, form.to_review) : t('dashboard.forms.allReviewed') }}</p>
      <div class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between text-xs"><span class="text-muted">{{ t('analytics.rate') }}</span><span class="text-highlighted tabular-nums">{{ number(form.completion_rate, { maximumFractionDigits: 1 }) }}%</span></div>
        <div class="h-1.5 overflow-hidden rounded-full bg-elevated"><div class="h-full rounded-full bg-inverted" :style="{ width: `${form.completion_rate}%` }" /></div>
      </div>
    </div>

    <div class="flex flex-col gap-2 border-t border-default pt-4">
      <h3 class="text-sm font-semibold text-highlighted">{{ t('dashboard.timeline.title') }}</h3>
      <USkeleton v-if="!data" class="h-20 w-full" />
      <p v-else-if="!data.timeline.length" class="text-xs text-muted">{{ t('dashboard.timeline.none') }}</p>
      <ol v-else class="flex flex-col">
        <li v-for="(item, i) in data.timeline.slice(0, 4)" :key="`${item.kind}-${item.at}-${i}`" class="relative flex items-center gap-3 py-1.5 ps-5">
          <span class="absolute start-0 top-1/2 flex size-3 -translate-y-1/2 items-center justify-center rounded-sm border border-inverted" :class="i === 0 ? 'bg-inverted' : 'bg-default'" />
          <span v-if="i < Math.min(data.timeline.length, 4) - 1" class="absolute start-[5px] top-1/2 h-full border-s border-dashed border-accented" />
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="text-[11px] text-muted">{{ date(item.at) }}</span>
            <span class="flex min-w-0 items-center gap-1.5 text-sm text-highlighted"><UIcon :name="ICON[item.kind]" class="size-3.5 shrink-0 text-muted" /><span class="truncate">{{ t(`dashboard.timeline.${item.kind}`, { name: item.kind === 'renews' || item.kind === 'plan_change' ? t(`billing.plan.${item.name}.name`) : (item.name ?? '') }) }}</span></span>
          </span>
          <UButton :label="t('dashboard.view')" trailing-icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" :to="item.link" />
        </li>
      </ol>
    </div>
  </UCard>
</template>
