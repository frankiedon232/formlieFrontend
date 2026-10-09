<!--
  Top of People (F16 M1; locked list format, rule 21): two equal chart cards. People: how many, who
  joined in the last 30 days (with the change), two-step sign-in and admins, sign-ins per day. By
  status: active · invited · disabled as thin lines; the legend filters the list.
-->
<script setup lang="ts">
import type { PeopleInsights } from '#shared/types/people'

const props = defineProps<{ insights: PeopleInsights | null; selected?: string | null }>()
const emit = defineEmits<{ pick: [key: string] }>()
const { t } = useI18n()
const { number } = useFormat()

const change = computed(() => (props.insights ? props.insights.joined - props.insights.joined_previous : 0))
const stats = computed(() => (props.insights ? [
  { label: t('people.stat.joined'), value: number(props.insights.joined) },
  { label: t('people.stat.twoStep'), value: `${number(props.insights.two_step)} / ${number(props.insights.total)}` },
] : []))
const parts = computed(() => [
  { key: 'active', label: t('people.status.active'), count: props.insights?.by_status.active ?? 0, color: 'bg-green-500' },
  { key: 'invited', label: t('people.status.invited'), count: props.insights?.by_status.invited ?? 0, color: 'bg-amber-500' },
  { key: 'disabled', label: t('people.status.disabled'), count: props.insights?.by_status.disabled ?? 0, color: 'bg-(--ui-border-accented)' },
])
</script>

<template>
  <div class="grid shrink-0 gap-4 lg:grid-cols-2">
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex flex-col">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('people.title') }}</h2>
        <span class="text-xs text-muted">{{ t('people.overviewHint') }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-5"><USkeleton class="h-16 w-40" /><USkeleton class="h-24 flex-1" /></div>
      <div v-else class="flex flex-1 items-end gap-5">
        <div class="flex shrink-0 flex-col gap-3">
          <div class="flex items-center gap-2.5">
            <UIcon name="i-lucide-users" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(insights.total) }}</span>
            <UBadge v-if="change" :label="`${change > 0 ? '+' : ''}${number(change)}`" :color="change > 0 ? 'success' : 'neutral'" variant="subtle" size="sm" class="rounded-md" />
          </div>
          <dl class="flex gap-4">
            <div v-for="stat in stats" :key="stat.label" class="flex min-w-0 flex-col">
              <dt class="truncate text-[11px] text-muted">{{ stat.label }}</dt>
              <dd class="truncate text-sm font-medium text-highlighted tabular-nums">{{ stat.value }}</dd>
            </div>
          </dl>
        </div>
        <ChartsMiniBars :days="insights.daily" :label="t('people.signIns')" />
      </div>
    </UCard>

    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('people.byStatus') }}</h2>
        <span class="text-xs text-muted tabular-nums">{{ t('people.total', { n: number(insights?.total ?? 0) }) }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end"><USkeleton class="h-24 flex-1" /></div>
      <div v-else class="flex flex-1 items-end gap-6">
        <ChartsLines :parts="parts" :selected="selected" class="min-w-0 flex-1" @pick="key => emit('pick', key)" />
        <ul class="hidden shrink-0 flex-col gap-1 sm:flex">
          <li v-for="part in parts" :key="part.key">
            <button type="button" class="flex w-full items-center gap-2 rounded-md px-1.5 py-0.5 text-start text-xs hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)" :class="selected === part.key ? 'bg-elevated' : ''" :aria-pressed="selected === part.key" @click="emit('pick', part.key)">
              <span class="size-2 shrink-0 rounded-[2px]" :class="part.color" /><span class="w-20 truncate text-default">{{ part.label }}</span><span class="ms-auto font-medium text-highlighted tabular-nums">{{ number(part.count) }}</span>
            </button>
          </li>
        </ul>
      </div>
    </UCard>
  </div>
</template>
