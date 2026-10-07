<!--
  Top of an organisation list (F14 M2; locked list format, rule 21): two equal chart cards. People:
  how many of the workspace's people belong to one (with entries, empty ones and archived ones), and
  the biggest entries as slim bars. By state: in use · empty · archived as thin lines, the legend
  filters the list.
-->
<script setup lang="ts">
import type { OrgInsights, OrgKind } from '#shared/types/org'

const props = defineProps<{ kind: OrgKind; insights: OrgInsights | null; selected?: string | null }>()
const emit = defineEmits<{ pick: [key: string] }>()
const { t } = useI18n()
const { number, percent } = useFormat()

const stats = computed(() => {
  const data = props.insights
  if (!data) return []
  return [
    { label: t(`settings.org.kind.${props.kind}.many`), value: number(data.by_status.active) },
    { label: t('settings.org.empty'), value: number(data.empty), warn: data.empty > 0 },
    { label: t('settings.org.archived'), value: number(data.by_status.archived) },
  ]
})
const parts = computed(() => [
  { key: 'in_use', label: t('settings.org.inUse'), count: props.insights ? props.insights.by_status.active - props.insights.empty : 0, color: 'bg-green-500' },
  { key: 'empty', label: t('settings.org.empty'), count: props.insights?.empty ?? 0, color: 'bg-amber-500' },
  { key: 'archived', label: t('settings.org.archived'), count: props.insights?.by_status.archived ?? 0, color: 'bg-(--ui-border-accented)' },
])
const points = computed(() => (props.insights?.largest ?? []).map(item => ({ label: item.name, value: item.count })))
</script>

<template>
  <div class="grid shrink-0 gap-4 lg:grid-cols-2">
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex flex-col">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('settings.org.people') }}</h2>
        <span class="text-xs text-muted">{{ t(`settings.org.kind.${kind}.peopleHint`) }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-5"><USkeleton class="h-16 w-48" /><USkeleton class="h-24 flex-1" /></div>
      <div v-else class="flex flex-1 items-end gap-5">
        <div class="flex shrink-0 flex-col gap-3">
          <div class="flex items-center gap-2.5">
            <UIcon name="i-lucide-users-round" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(insights.people_assigned) }}</span>
            <div class="flex flex-col gap-0.5">
              <UBadge :label="percent(insights.people ? insights.people_assigned / insights.people : 0)" :color="insights.people_assigned === insights.people ? 'success' : 'neutral'" variant="subtle" size="sm" class="w-fit rounded-md tabular-nums" />
              <span class="text-[11px] text-muted">{{ t('settings.org.ofPeople', { n: number(insights.people) }) }}</span>
            </div>
          </div>
          <dl class="flex gap-4">
            <div v-for="stat in stats" :key="stat.label" class="flex min-w-0 flex-col">
              <dt class="truncate text-[11px] text-muted">{{ stat.label }}</dt>
              <dd class="truncate text-sm font-medium tabular-nums" :class="stat.warn ? 'text-warning' : 'text-highlighted'">{{ stat.value }}</dd>
            </div>
          </dl>
        </div>
        <ChartsBars v-if="points.length" :points="points" height="h-24" :axis="0" :unit="n => t('settings.org.peopleCount', { n }, n)" class="hidden min-w-0 flex-1 sm:block" />
      </div>
    </UCard>

    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('settings.org.byState') }}</h2>
        <span class="text-xs text-muted tabular-nums">{{ t('settings.org.total', { n: number(insights?.total ?? 0) }) }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-6"><USkeleton class="h-24 flex-1" /></div>
      <AppEmpty v-else-if="!insights.total" size="xs" icon="i-lucide-network" :title="t(`settings.org.kind.${kind}.empty`)" />
      <div v-else class="flex flex-1 items-end gap-6">
        <ChartsLines :parts="parts" :selected="selected" class="min-w-0 flex-1" @pick="key => emit('pick', key)" />
        <ul class="hidden shrink-0 flex-col gap-1 sm:flex">
          <li v-for="part in parts" :key="part.key">
            <button type="button" class="flex w-full items-center gap-2 rounded-md px-1.5 py-0.5 text-start text-xs hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)" :class="selected === part.key ? 'bg-elevated' : ''" :aria-pressed="selected === part.key" @click="emit('pick', part.key)">
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
