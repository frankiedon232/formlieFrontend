<!--
  Top of List Option (F15 M1; locked list format, rule 21): two equal chart cards. Options: how many
  options all lists hold (with lists and retired ones) and the biggest lists as slim bars. By state:
  in use · not used yet · with retired options as thin lines; the legend filters the list.
-->
<script setup lang="ts">
import type { OptionListInsights } from '#shared/types/forms'

const props = defineProps<{ insights: OptionListInsights | null; selected?: string | null }>()
const emit = defineEmits<{ pick: [key: string] }>()
const { t } = useI18n()
const { number } = useFormat()

const stats = computed(() => (props.insights ? [
  { label: t('optionSets.stat.lists'), value: number(props.insights.total) },
  { label: t('optionSets.stat.retired'), value: number(props.insights.retired) },
] : []))
const parts = computed(() => [
  { key: 'in_use', label: t('optionSets.state.in_use'), count: props.insights?.in_use ?? 0, color: 'bg-green-500' },
  { key: 'unused', label: t('optionSets.state.unused'), count: props.insights?.unused ?? 0, color: 'bg-amber-500' },
  { key: 'retired', label: t('optionSets.state.retired'), count: 0, color: 'bg-(--ui-border-accented)' },
].filter(part => part.key !== 'retired'))
const points = computed(() => (props.insights?.largest ?? []).map(item => ({ label: item.name, value: item.count })))
</script>

<template>
  <div class="grid shrink-0 gap-4 lg:grid-cols-2">
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex flex-col">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('optionSets.options') }}</h2>
        <span class="text-xs text-muted">{{ t('optionSets.optionsHint') }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-5"><USkeleton class="h-16 w-40" /><USkeleton class="h-24 flex-1" /></div>
      <div v-else class="flex flex-1 items-end gap-5">
        <div class="flex shrink-0 flex-col gap-3">
          <div class="flex items-center gap-2.5">
            <UIcon name="i-lucide-list-checks" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(insights.items) }}</span>
          </div>
          <dl class="flex gap-4">
            <div v-for="stat in stats" :key="stat.label" class="flex min-w-0 flex-col">
              <dt class="truncate text-[11px] text-muted">{{ stat.label }}</dt>
              <dd class="truncate text-sm font-medium text-highlighted tabular-nums">{{ stat.value }}</dd>
            </div>
          </dl>
        </div>
        <ChartsBars v-if="points.length > 1" :points="points" height="h-24" :axis="0" :unit="n => t('optionSets.itemsCount', { n }, n)" class="hidden min-w-0 flex-1 sm:block" />
      </div>
    </UCard>

    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('optionSets.byState') }}</h2>
        <span class="text-xs text-muted tabular-nums">{{ t('optionSets.total', { n: number(insights?.total ?? 0) }) }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end"><USkeleton class="h-24 flex-1" /></div>
      <AppEmpty v-else-if="!insights.total" size="xs" icon="i-lucide-list-checks" :title="t('optionSets.empty')" />
      <div v-else class="flex flex-1 items-end gap-6">
        <ChartsLines :parts="parts" :selected="selected" class="min-w-0 flex-1" @pick="key => emit('pick', key)" />
        <ul class="hidden shrink-0 flex-col gap-1 sm:flex">
          <li v-for="part in parts" :key="part.key">
            <button type="button" class="flex w-full items-center gap-2 rounded-md px-1.5 py-0.5 text-start text-xs hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)" :class="selected === part.key ? 'bg-elevated' : ''" :aria-pressed="selected === part.key" @click="emit('pick', part.key)">
              <span class="size-2 shrink-0 rounded-[2px]" :class="part.color" /><span class="w-24 truncate text-default">{{ part.label }}</span><span class="ms-auto font-medium text-highlighted tabular-nums">{{ number(part.count) }}</span>
            </button>
          </li>
        </ul>
      </div>
    </UCard>
  </div>
</template>
