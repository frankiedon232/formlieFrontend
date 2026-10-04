<!--
  Category card in the locked card format (CLAUDE.md rule 21, owner 2026-10-04): a "last used" pill,
  the template count and ⋯ on top; the category's design in miniature beside its name and a few of
  its templates; templates, with calculations, forms and responses in two columns; a divider, then
  Share of use with a black bar (its forms out of all forms made from templates); icon, key and
  what its templates hold at the bottom. The whole card opens the category (DataView openRow).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { TemplateCategorySummary } from '#shared/types/templates'
import { categoryOf } from '#shared/templates/categories'

const props = defineProps<{
  category: TemplateCategorySummary
  actions: DropdownMenuItem[][]
  total?: number
}>()
const { t } = useI18n()
const { relative, number, percent } = useFormat()
const dot = computed(() => categoryOf(props.category.key)?.dot)
const share = computed(() => (props.total ? props.category.forms_count / props.total : 0))
const facts = computed(() => [
  { key: 'templates', label: t('templates.col.templates'), value: number(props.category.templates_count) },
  {
    key: 'calculations',
    label: t('templates.badge.calculations'),
    value: number(props.category.calculations_count),
  },
  { key: 'forms', label: t('templates.col.forms'), value: number(props.category.forms_count) },
  { key: 'responses', label: t('templates.col.responses'), value: number(props.category.responses_count) },
])
</script>

<template>
  <article
    class="group flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md"
  >
    <!-- Last used · templates · menu -->
    <div class="flex items-center justify-between gap-2">
      <span
        class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned"
      >
        <UIcon name="i-lucide-clock-3" class="size-3.5 shrink-0 text-muted" />
        <span class="truncate">{{
          category.last_used_at
            ? t('templates.card.used', { when: relative(category.last_used_at) })
            : t('templates.neverUsed')
        }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <UBadge
          :label="
            t(
              'templates.categoryCard.templates',
              { count: category.templates_count },
              category.templates_count,
            )
          "
          color="neutral"
          variant="outline"
          size="sm"
          class="tabular-nums"
        />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton
            icon="i-lucide-ellipsis"
            color="neutral"
            variant="outline"
            size="xs"
            square
            :aria-label="t('dataView.actions')"
          />
        </UDropdownMenu>
      </div>
    </div>

    <!-- Design, name and examples -->
    <div class="mt-3 flex min-w-0 items-center gap-3">
      <span class="w-14 shrink-0 overflow-hidden rounded-sm border border-default" aria-hidden="true">
        <TemplatesThumb :theme="category.theme" :title="category.name" :labels="category.examples" mini />
      </span>
      <div class="flex min-w-0 flex-col">
        <NuxtLink
          :to="`/templates/category/${category.key}`"
          class="flex min-w-0 items-center gap-1.5 text-base font-semibold text-highlighted hover:underline focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
        >
          <span class="size-2 shrink-0 rounded-[1px]" :class="dot" aria-hidden="true" />
          <span class="truncate">{{ category.name }}</span>
        </NuxtLink>
        <p class="truncate text-sm text-muted">{{ category.examples.join(' · ') }}</p>
      </div>
    </div>

    <!-- Facts (two columns, one line each) -->
    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd
          class="h-5 truncate text-sm tabular-nums"
          :class="fact.key === 'forms' ? 'font-medium text-highlighted' : 'text-default'"
        >
          {{ fact.value }}
        </dd>
      </div>
    </dl>

    <!-- Share of use (the design's Progress) -->
    <div class="mt-auto pt-4">
      <div class="border-t border-default pt-3">
        <div class="mb-1.5 flex items-center justify-between text-xs">
          <span class="text-muted">{{ t('templates.card.share') }}</span>
          <span class="font-medium text-highlighted tabular-nums">{{ percent(share) }}</span>
        </div>
        <div class="h-1.5 overflow-hidden rounded-full bg-elevated" role="presentation">
          <div class="h-full rounded-full bg-inverted" :style="{ width: `${share * 100}%` }" />
        </div>
      </div>

      <!-- Icon, key, what its templates hold -->
      <div class="mt-4 flex items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-2">
          <UAvatar :icon="category.icon" size="xs" />
          <span class="truncate font-mono text-xs text-muted">{{ category.key }}</span>
        </div>
        <div class="flex shrink-0 items-center gap-3 text-xs text-muted">
          <UTooltip :text="t('templates.badge.logic')">
            <span class="flex items-center gap-1" :class="category.logic_count ? 'text-toned' : ''"
              ><UIcon name="i-lucide-git-branch" class="size-3.5" />{{ category.logic_count }}</span
            >
          </UTooltip>
          <UTooltip :text="t('templates.col.responses')">
            <span class="flex items-center gap-1" :class="category.responses_count ? 'text-toned' : ''"
              ><UIcon name="i-lucide-inbox" class="size-3.5" />{{ number(category.responses_count) }}</span
            >
          </UTooltip>
        </div>
      </div>
    </div>
  </article>
</template>
