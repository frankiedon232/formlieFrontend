<!--
  Theme card in the locked card format (CLAUDE.md rule 21, owner 2026-10-04; same structure as the
  form, response and template cards): a "changed" pill, the kind and ⋯ on top; the theme in
  miniature beside its name, font and layout; forms, kind, created by and created in two columns; a
  divider, then Share of forms with a black bar (forms styled with it out of all forms); author,
  short id and the theme's colours at the bottom. The whole card opens the theme (DataView openRow).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { SavedTheme } from '#shared/types/forms'

const props = defineProps<{
  theme: SavedTheme
  name: string
  actions: DropdownMenuItem[][]
  busy?: boolean
  total?: number
  preview: string[]
}>()
const { t } = useI18n()
const { relative, date, number, percent } = useFormat()
const SOURCE_ICON: Record<SavedTheme['source'], string> = {
  system: 'i-lucide-sparkles',
  saved: 'i-lucide-bookmark',
  created: 'i-lucide-paintbrush',
}
const share = computed(() => (props.total ? props.theme.forms_count / props.total : 0))
/** The theme's main colours as small swatches: accent, text, page and form background. */
const swatches = computed(() => [
  ...new Set([
    props.theme.tokens.colors.primary,
    props.theme.tokens.colors.text,
    props.theme.tokens.page.bg,
    props.theme.tokens.container.bg,
  ]),
])
const facts = computed(() => [
  { key: 'forms', label: t('themes.col.forms'), value: number(props.theme.forms_count) },
  { key: 'kind', label: t('themes.filterSource'), value: t(`themes.source.${props.theme.source}`) },
  { key: 'by', label: t('themes.col.createdBy'), value: props.theme.created_by.name },
  { key: 'created', label: t('themes.card.created'), value: date(props.theme.created_at) },
])
</script>

<template>
  <article
    class="group flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md"
  >
    <!-- Changed · kind · menu -->
    <div class="flex items-center justify-between gap-2">
      <span
        class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned"
      >
        <UIcon
          :name="busy ? 'i-lucide-loader-circle' : 'i-lucide-clock-3'"
          class="size-3.5 shrink-0 text-muted"
          :class="busy ? 'animate-spin' : ''"
        />
        <span class="truncate">{{ t('themes.card.changed', { when: relative(theme.updated_at) }) }}</span>
      </span>
      <div class="flex min-w-0 items-center gap-1.5">
        <UBadge
          :label="t(`themes.source.${theme.source}`)"
          :icon="SOURCE_ICON[theme.source]"
          color="neutral"
          variant="outline"
          size="sm"
          class="min-w-0 truncate"
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

    <!-- Preview, name and font -->
    <div class="mt-3 flex min-w-0 items-center gap-3">
      <span class="w-14 shrink-0 overflow-hidden rounded-sm border border-default" aria-hidden="true">
        <TemplatesThumb :theme="theme.tokens" :title="name" :labels="preview" mini />
      </span>
      <div class="flex min-w-0 flex-col">
        <NuxtLink
          :to="`/settings/themes/${theme.id}`"
          class="truncate text-base font-semibold text-highlighted hover:underline focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
          >{{ name }}</NuxtLink
        >
        <p class="flex min-w-0 items-center gap-1.5 text-sm text-muted">
          <UIcon name="i-lucide-type" class="size-3.5 shrink-0" />
          <span class="truncate"
            >{{ t(`designer.font.${theme.tokens.typography.font}`) }} ·
            {{ t(`designer.layout.${theme.tokens.layout}`) }}</span
          >
        </p>
      </div>
    </div>

    <!-- Facts (two columns, one line each) -->
    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd
          class="h-5 truncate text-sm"
          :class="fact.key === 'forms' ? 'font-medium text-highlighted tabular-nums' : 'text-default'"
        >
          {{ fact.value }}
        </dd>
      </div>
    </dl>

    <!-- Share of forms (the design's Progress) -->
    <div class="mt-auto pt-4">
      <div class="border-t border-default pt-3">
        <div class="mb-1.5 flex items-center justify-between text-xs">
          <span class="text-muted">{{ t('themes.card.share') }}</span>
          <span class="font-medium text-highlighted tabular-nums">{{ percent(share) }}</span>
        </div>
        <div class="h-1.5 overflow-hidden rounded-full bg-elevated" role="presentation">
          <div class="h-full rounded-full bg-inverted" :style="{ width: `${share * 100}%` }" />
        </div>
      </div>

      <!-- Author, id, colours -->
      <div class="mt-4 flex items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-2">
          <UAvatar :alt="theme.created_by.name" size="xs" />
          <span class="truncate font-mono text-xs text-muted">{{ theme.id.slice(0, 12) }}</span>
        </div>
        <div class="flex shrink-0 -space-x-1 rtl:space-x-reverse" :aria-label="t('themes.card.colours')">
          <span
            v-for="colour in swatches"
            :key="colour"
            class="size-4 rounded-full ring-2 ring-(--ui-bg)"
            :style="{ backgroundColor: colour }"
            :title="colour"
          />
        </div>
      </div>
    </div>
  </article>
</template>
