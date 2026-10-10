<!--
  Top of the AI assistant pages (locked list format, rule 21): two equal chart cards. Credits used this
  month (with the change against the same days of last month, the allowance, requests and people, and
  credits per day) and requests by kind as thin lines; the legend picks a kind.
-->
<script setup lang="ts">
import { AI_KINDS, type AiKind, type AiUsage } from '#shared/types/ai'

const props = defineProps<{ usage: AiUsage | null; byKind: Record<AiKind, number> | null; kind?: string | null; kindsTitle: string; kindsNote?: string }>()
const emit = defineEmits<{ kind: [kind: AiKind] }>()
const { t } = useI18n()
const { number } = useFormat()

const trend = computed(() => (props.usage?.previous ? Math.round(((props.usage.used - props.usage.previous) / props.usage.previous) * 100) : null))
const left = computed(() => (props.usage ? Math.max(0, props.usage.limit - props.usage.used) : 0))
const stats = computed(() =>
  props.usage
    ? [
        { label: t('ai.usage.allowance'), value: number(props.usage.limit) },
        { label: t('ai.usage.requests'), value: number(props.usage.requests) },
        { label: t('ai.usage.people'), value: number(props.usage.people) },
      ]
    : [],
)
// Ink first, then the theme's colours (monochrome with status accents, rule 21)
const COLORS = ['bg-(--ui-text-highlighted)', 'bg-(--ui-text-muted)', 'bg-amber-500', 'bg-green-500', 'bg-violet-500', 'bg-red-500', 'bg-(--ui-text-dimmed)', 'bg-amber-300', 'bg-green-300']
const parts = computed(() =>
  AI_KINDS.map(key => ({ key, label: t(`ai.kind.${key}`), count: props.byKind?.[key] ?? 0 }))
    .filter(part => part.count > 0)
    .sort((a, b) => b.count - a.count)
    .map((part, index) => ({ ...part, color: COLORS[index]! })),
)
</script>

<template>
  <div class="grid gap-4 lg:grid-cols-2">
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <div class="flex flex-col">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('ai.usage.title') }}</h2>
          <span class="text-xs text-muted">{{ t('ai.usage.thisMonth') }}</span>
        </div>
        <span v-if="usage" class="text-xs text-muted tabular-nums">{{ t('ai.usage.left', { n: number(left) }) }}</span>
      </div>
      <div v-if="!usage" class="flex flex-1 items-end gap-5"><USkeleton class="h-16 w-48" /><USkeleton class="h-24 flex-1" /></div>
      <div v-else class="flex flex-1 items-end gap-5">
        <div class="flex shrink-0 flex-col gap-3">
          <div class="flex items-center gap-2.5">
            <UIcon name="i-lucide-sparkles" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(usage.used) }}</span>
            <div class="flex flex-col gap-0.5">
              <UBadge v-if="trend !== null" :label="`${trend > 0 ? '+' : ''}${trend}%`" color="neutral" variant="subtle" size="sm" class="w-fit rounded-md tabular-nums" />
              <span class="text-[11px] text-muted">{{ t('ai.usage.vsLastMonth') }}</span>
            </div>
          </div>
          <dl class="flex gap-4">
            <div v-for="stat in stats" :key="stat.label" class="flex min-w-0 flex-col">
              <dt class="truncate text-[11px] text-muted">{{ stat.label }}</dt>
              <dd class="truncate text-sm font-medium text-highlighted tabular-nums">{{ stat.value }}</dd>
            </div>
          </dl>
        </div>
        <ChartsMiniBars :days="usage.daily" :label="t('ai.usage.perDay')" />
      </div>
    </UCard>

    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ kindsTitle }}</h2>
        <span v-if="kindsNote" class="text-xs text-muted">{{ kindsNote }}</span>
      </div>
      <div v-if="!byKind" class="flex flex-1 items-end gap-6"><USkeleton class="h-24 flex-1" /></div>
      <AppEmpty v-else-if="!parts.length" icon="i-lucide-sparkles" size="xs" :title="t('ai.history.none')" />
      <div v-else class="flex flex-1 items-end gap-6">
        <ChartsLines :parts="parts" :selected="kind" class="min-w-0 flex-1" @pick="key => emit('kind', key as AiKind)" />
        <ul class="hidden max-h-28 shrink-0 flex-col gap-1 overflow-y-auto sm:flex">
          <li v-for="part in parts" :key="part.key">
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-md px-1.5 py-0.5 text-start text-xs hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :class="kind === part.key ? 'bg-elevated' : ''"
              :aria-pressed="kind === part.key"
              @click="emit('kind', part.key)"
            >
              <span class="size-2 shrink-0 rounded-[2px]" :class="part.color" />
              <span class="w-32 truncate text-default">{{ part.label }}</span>
              <span class="ms-auto font-medium text-highlighted tabular-nums">{{ number(part.count) }}</span>
            </button>
          </li>
        </ul>
      </div>
    </UCard>
  </div>
</template>
