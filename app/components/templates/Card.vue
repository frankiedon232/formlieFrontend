<!--
  Template card in the locked card format (CLAUDE.md rule 21, owner 2026-10-04; same structure as
  the form and response cards): a "last used" pill, the category and ⋯ (Use first) on top; the
  template's design in miniature beside its name and how long it takes; questions, pages, forms
  and responses in two columns; a divider, then Share of use with a black bar (its forms out of all
  forms made from templates); author, key and what it holds (calculations, logic) at the bottom.
  The whole card opens the template (DataView openRow).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { TemplateSummary } from '#shared/types/templates'
import { categoryOf } from '#shared/templates/categories'

const props = defineProps<{
  template: TemplateSummary
  actions: DropdownMenuItem[][]
  busy?: boolean
  total?: number
}>()
const { t } = useI18n()
const { relative, number, percent } = useFormat()
const category = computed(() => categoryOf(props.template.category))
const share = computed(() => (props.total ? props.template.forms_count / props.total : 0))
const facts = computed(() => [
  { key: 'questions', label: t('templates.col.questions'), value: number(props.template.fields_count) },
  { key: 'pages', label: t('templates.card.pages'), value: number(props.template.pages_count) },
  { key: 'forms', label: t('templates.col.forms'), value: number(props.template.forms_count) },
  { key: 'responses', label: t('templates.col.responses'), value: number(props.template.responses_count) },
])
</script>

<template>
  <article
    class="group flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md"
  >
    <!-- Last used · category · menu -->
    <div class="flex items-center justify-between gap-2">
      <span
        class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned"
      >
        <UIcon
          :name="busy ? 'i-lucide-loader-circle' : 'i-lucide-clock-3'"
          class="size-3.5 shrink-0 text-muted"
          :class="busy ? 'animate-spin' : ''"
        />
        <span class="truncate">{{
          template.last_used_at
            ? t('templates.card.used', { when: relative(template.last_used_at) })
            : t('templates.neverUsed')
        }}</span>
      </span>
      <div class="flex min-w-0 items-center gap-1.5">
        <UBadge color="neutral" variant="outline" size="sm" class="min-w-0 gap-1.5">
          <span class="size-2 shrink-0 rounded-[1px]" :class="category?.dot" aria-hidden="true" />
          <span class="truncate">{{ t(`templates.categories.${template.category}`) }}</span>
        </UBadge>
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

    <!-- Design, name and time -->
    <div class="mt-3 flex min-w-0 items-center gap-3">
      <span class="w-14 shrink-0 overflow-hidden rounded-sm border border-default" aria-hidden="true">
        <TemplatesThumb :theme="template.theme" :title="template.name" :labels="template.preview" mini />
      </span>
      <div class="flex min-w-0 flex-col">
        <NuxtLink
          :to="`/templates/${template.key}`"
          class="truncate text-base font-semibold text-highlighted hover:underline focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
          >{{ template.name }}</NuxtLink
        >
        <p class="flex min-w-0 items-center gap-1.5 text-sm text-muted">
          <UIcon
            :name="template.source === 'workspace' ? 'i-lucide-building-2' : 'i-lucide-timer'"
            class="size-3.5 shrink-0"
          />
          <span class="truncate">{{
            template.source === 'workspace'
              ? t('templates.badge.workspace')
              : t('templates.minutes', { n: template.minutes })
          }}</span>
        </p>
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

      <!-- Author, key, what it holds -->
      <div class="mt-4 flex items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-2">
          <UAvatar :alt="template.created_by?.name ?? 'Formalie'" size="xs" />
          <span class="truncate font-mono text-xs text-muted">{{ template.key }}</span>
        </div>
        <div class="flex shrink-0 items-center gap-3 text-xs text-muted">
          <UTooltip :text="t('templates.badge.calculations')">
            <span class="flex items-center gap-1" :class="template.calculations_count ? 'text-toned' : ''"
              ><UIcon name="i-lucide-calculator" class="size-3.5" />{{ template.calculations_count }}</span
            >
          </UTooltip>
          <UTooltip :text="t('templates.badge.logic')">
            <span class="flex items-center gap-1" :class="template.logic_count ? 'text-toned' : ''"
              ><UIcon name="i-lucide-git-branch" class="size-3.5" />{{ template.logic_count }}</span
            >
          </UTooltip>
        </div>
      </div>
    </div>
  </article>
</template>
