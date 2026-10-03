<!--
  Category card (owner, 2026-10-03): the templates gallery opens on Formalie's categories instead of
  every template. Each card shows the category's design in miniature with a few of its templates,
  how many templates it holds (with calculations / logic) and how they're used. The whole card opens
  the category.
-->
<script setup lang="ts">
import type { TemplateCategorySummary } from '#shared/types/templates'
import { categoryOf } from '#shared/templates/categories'

const props = defineProps<{ category: TemplateCategorySummary }>()
const { t } = useI18n()
const { compact, relative } = useFormat()
const dot = computed(() => categoryOf(props.category.key)?.dot)
</script>

<template>
  <article class="group/card relative flex h-full flex-col overflow-hidden rounded-lg border border-default bg-default transition-colors hover:border-accented">
    <TemplatesThumb :theme="category.theme" :title="category.name" :labels="category.examples" />
    <div class="flex flex-1 flex-col gap-2 border-t border-default p-3">
      <div class="flex items-start gap-2">
        <UIcon :name="category.icon" class="mt-0.5 size-4 shrink-0 text-muted" />
        <NuxtLink
          :to="`/templates/category/${category.key}`"
          class="min-w-0 flex-1 font-medium text-highlighted after:absolute after:inset-0 focus-visible:outline-none after:focus-visible:rounded-lg after:focus-visible:outline-2 after:focus-visible:outline-(--ui-border-inverted)"
        >
          <span class="flex items-center gap-1.5">
            <span class="size-2 shrink-0 rounded-[1px]" :class="dot" aria-hidden="true" />
            <span class="line-clamp-1">{{ category.name }}</span>
          </span>
        </NuxtLink>
        <UBadge :label="compact(category.templates_count)" color="neutral" variant="outline" size="sm" class="tabular-nums" />
      </div>
      <p class="line-clamp-2 text-xs text-muted">{{ category.examples.join(' · ') }}</p>
      <div class="mt-auto flex flex-wrap items-center gap-1.5 pt-1">
        <UBadge
          :label="t('templates.categoryCard.templates', { count: category.templates_count }, category.templates_count)"
          icon="i-lucide-layout-template"
          color="neutral"
          variant="outline"
          size="sm"
        />
        <UBadge v-if="category.calculations_count" :label="`${t('templates.badge.calculations')} · ${category.calculations_count}`" icon="i-lucide-calculator" color="neutral" variant="soft" size="sm" />
        <UBadge v-if="category.logic_count" :label="`${t('templates.badge.logic')} · ${category.logic_count}`" icon="i-lucide-git-branch" color="neutral" variant="soft" size="sm" />
      </div>
      <div class="flex items-center justify-between gap-2 text-xs text-muted">
        <span class="flex items-center gap-3">
          <span class="flex items-center gap-1" :title="t('templates.col.forms')"><UIcon name="i-lucide-file-text" class="size-3.5" />{{ compact(category.forms_count) }}</span>
          <span class="flex items-center gap-1" :title="t('templates.col.responses')"><UIcon name="i-lucide-inbox" class="size-3.5" />{{ compact(category.responses_count) }}</span>
        </span>
        <span class="truncate">{{ category.last_used_at ? relative(category.last_used_at) : t('templates.neverUsed') }}</span>
      </div>
      <UButton
        :label="t('templates.categoryCard.browse')"
        trailing-icon="i-lucide-arrow-right"
        color="neutral"
        variant="outline"
        size="sm"
        block
        class="relative z-10"
        :to="`/templates/category/${category.key}`"
      />
    </div>
  </article>
</template>
