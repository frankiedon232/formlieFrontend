<!--
  The top of the template pages (locked list-page format, CLAUDE.md rule 21; owner 2026-10-04):
  two equal cards with charts. Forms from templates (last 30 days): count with its change, Formalie
  templates, your templates, all-time forms, and the daily bars. Use by category: the design's thin
  lines for the five most used categories (ink shades, the rest as Other); a category opens its page.
-->
<script setup lang="ts">
import type { TemplateInsights } from '#shared/types/templates'

const props = defineProps<{ insights: TemplateInsights | null; category?: string | null }>()
const { t } = useI18n()
const { number } = useFormat()

const trend = computed(() => {
  const period = props.insights?.period
  return period?.previous ? Math.round(((period.count - period.previous) / period.previous) * 100) : null
})
const stats = computed(() => [
  { label: t('templates.overview.system'), value: number(props.insights?.system_count ?? 0) },
  { label: t('templates.overview.mine'), value: number(props.insights?.workspace_count ?? 0) },
  { label: t('templates.overview.allTime'), value: number(props.insights?.forms_total ?? 0) },
])
const SHADES = ['bg-inverted', 'bg-inverted/75', 'bg-inverted/55', 'bg-inverted/35', 'bg-inverted/20']
const parts = computed(() => {
  const all = props.insights?.categories ?? []
  const top = all
    .slice(0, 5)
    .map((item, index) => ({
      key: item.key,
      label: t(`templates.categories.${item.key}`),
      count: item.forms,
      color: SHADES[index]!,
    }))
  const rest = all.slice(5).reduce((sum, item) => sum + item.forms, 0)
  return rest
    ? [
        ...top,
        {
          key: 'other',
          label: t('templates.overview.other'),
          count: rest,
          color: 'bg-(--ui-border-accented)',
        },
      ]
    : top
})
const open = (key: string) => key !== 'other' && navigateTo(`/templates/category/${key}`)
</script>

<template>
  <div class="grid gap-4 lg:grid-cols-2">
    <!-- Forms from templates -->
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <div class="flex flex-col">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('templates.overview.formsFrom') }}</h2>
          <span class="text-xs text-muted">{{ t('forms.overview.last30Short') }}</span>
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
      <div v-if="insights" class="flex flex-1 items-end gap-5">
        <div class="flex shrink-0 flex-col gap-3">
          <div class="flex items-center gap-2.5">
            <UIcon name="i-lucide-file-plus" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{
              number(insights.period.count)
            }}</span>
            <div class="flex flex-col gap-0.5">
              <UBadge
                v-if="trend !== null"
                :label="`${trend > 0 ? '+' : ''}${trend}%`"
                :color="trend >= 0 ? 'success' : 'error'"
                variant="subtle"
                size="sm"
                class="w-fit rounded-md tabular-nums"
              />
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
        <ChartsMiniBars :days="insights.daily" :label="t('templates.overview.formsFrom')" />
      </div>
      <div v-else class="flex flex-1 items-end gap-5">
        <USkeleton class="h-16 w-40" />
        <USkeleton class="hidden h-24 flex-1 sm:block" />
      </div>
    </UCard>

    <!-- Use by category -->
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('templates.overview.byCategory') }}</h2>
        <span class="text-xs text-muted">{{
          t('templates.overview.formsCount', { n: number(insights?.forms_total ?? 0) })
        }}</span>
      </div>
      <div v-if="insights && parts.length" class="flex flex-1 items-end gap-6">
        <ChartsLines :parts="parts" :selected="category" class="min-w-0 flex-1" @pick="open" />
        <ul class="hidden shrink-0 flex-col gap-1 sm:flex">
          <li v-for="part in parts" :key="part.key">
            <component
              :is="part.key === 'other' ? 'span' : 'button'"
              :type="part.key === 'other' ? undefined : 'button'"
              class="flex w-full items-center gap-2 rounded-md px-1.5 py-0.5 text-start text-xs focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :class="[
                part.key === 'other' ? '' : 'hover:bg-elevated',
                category === part.key ? 'bg-elevated' : '',
              ]"
              :aria-current="category === part.key ? 'page' : undefined"
              @click="open(part.key)"
            >
              <span class="size-2 shrink-0 rounded-[2px]" :class="part.color" />
              <span class="w-28 truncate text-default">{{ part.label }}</span>
              <span class="ms-auto font-medium text-highlighted tabular-nums">{{ number(part.count) }}</span>
            </component>
          </li>
        </ul>
      </div>
      <UEmpty
        v-else-if="insights"
        icon="i-lucide-shapes"
        :title="t('templates.overview.noUse')"
        variant="naked"
        size="sm"
        class="flex-1"
      />
      <USkeleton v-else class="h-24 w-full" />
    </UCard>
  </div>
</template>
