<!--
  Theme card (locked card format, CLAUDE.md rule 21; owner 2026-10-04: thumbnail left, content
  right, then buttons, then details, nothing more). The theme in a fixed 16:9 frame beside its name,
  font and layout; a row with the "changed" pill, the kind and ⋯; forms, kind, created by and
  created in two columns. The whole card opens the theme (DataView openRow).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { SavedTheme } from '#shared/types/forms'

const props = defineProps<{
  theme: SavedTheme
  name: string
  actions: DropdownMenuItem[][]
  busy?: boolean
  preview: string[]
}>()
const { t } = useI18n()
const { relative, date, number } = useFormat()
const SOURCE_ICON: Record<SavedTheme['source'], string> = {
  system: 'i-lucide-sparkles',
  saved: 'i-lucide-bookmark',
  created: 'i-lucide-paintbrush',
}
const facts = computed(() => [
  { key: 'forms', label: t('themes.col.forms'), value: number(props.theme.forms_count) },
  { key: 'kind', label: t('themes.filterSource'), value: t(`themes.source.${props.theme.source}`) },
  { key: 'by', label: t('themes.col.createdBy'), value: props.theme.created_by.name },
  { key: 'created', label: t('themes.card.created'), value: date(props.theme.created_at) },
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
        <TemplatesThumb :theme="theme.tokens" :title="name" :labels="preview" tile />
      </span>
      <div class="flex min-w-0 flex-1 flex-col gap-1">
        <NuxtLink
          :to="`/settings/themes/${theme.id}`"
          class="line-clamp-2 text-base leading-snug font-semibold text-highlighted hover:underline focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
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

    <!-- Buttons: Changed · kind · menu -->
    <div class="mt-auto flex items-center justify-between gap-2 border-t border-default pt-3">
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

    <!-- Details (two columns, one line each) -->
    <dl class="grid grid-cols-2 gap-x-4 gap-y-2.5">
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
  </article>
</template>
