<!--
  Template card (locked card format, CLAUDE.md rule 21; owner 2026-10-04: thumbnail left, content
  right, then buttons, then details, nothing more). The template's design in a fixed 16:9 frame
  (every card's picture the same size) beside its name and time to fill in; a row with the "last
  used" pill, the category and ⋯ (Use first); questions, pages, forms and responses in two columns.
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
}>()
const { t } = useI18n()
const { relative, number } = useFormat()
const category = computed(() => categoryOf(props.template.category))
const facts = computed(() => [
  { key: 'questions', label: t('templates.col.questions'), value: number(props.template.fields_count) },
  { key: 'pages', label: t('templates.card.pages'), value: number(props.template.pages_count) },
  { key: 'forms', label: t('templates.col.forms'), value: number(props.template.forms_count) },
  { key: 'responses', label: t('templates.col.responses'), value: number(props.template.responses_count) },
])
</script>

<template>
  <article
    class="group flex h-full flex-col gap-3 rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md"
  >
    <!-- Thumbnail left, name and subtitle right -->
    <div class="flex min-w-0 items-center gap-3">
      <span
        class="w-32 shrink-0 overflow-hidden rounded-md border border-default bg-elevated sm:w-36"
        aria-hidden="true"
      >
        <TemplatesThumb :theme="template.theme" :title="template.name" :labels="template.preview" tile />
      </span>
      <div class="flex min-w-0 flex-1 flex-col gap-1">
        <NuxtLink
          :to="`/templates/${template.key}`"
          class="line-clamp-2 text-base leading-snug font-semibold text-highlighted hover:underline focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
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

    <!-- Buttons: Last used · category · menu -->
    <div class="mt-auto flex items-center justify-between gap-2 border-t border-default pt-3">
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

    <!-- Details (two columns, one line each) -->
    <dl class="grid grid-cols-2 gap-x-4 gap-y-2.5">
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
  </article>
</template>
