<!--
  Page design card (Resources → Landing pages; same arrangement as the theme card, owner 2026-10-04:
  thumbnail left, content right, then buttons, then details). The page in a fixed 16:9 miniature
  beside its name and style · tone; a row with the "changed" pill, the kind and ⋯; forms, kind,
  created by and created in two columns. The whole card opens the design (DataView openRow).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { PageDesign } from '#shared/types/forms'

const props = defineProps<{ page: PageDesign; name: string; actions: DropdownMenuItem[][]; busy?: boolean }>()
const { t } = useI18n()
const { relative, date, number } = useFormat()
const SOURCE_ICON: Record<PageDesign['source'], string> = { system: 'i-lucide-sparkles', saved: 'i-lucide-bookmark', created: 'i-lucide-paintbrush' }
const facts = computed(() => [
  { key: 'forms', label: t('themes.col.forms'), value: t('themes.formsCount', { count: number(props.page.forms_count) }, props.page.forms_count) },
  { key: 'kind', label: t('themes.filterSource'), value: t(`themes.source.${props.page.source}`) },
  { key: 'by', label: t('themes.col.createdBy'), value: props.page.created_by.name },
  { key: 'created', label: t('themes.card.created'), value: date(props.page.created_at) },
])
</script>

<template>
  <article class="group flex h-full flex-col gap-3 rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md">
    <!-- Thumbnail left, name and style right -->
    <div class="flex min-w-0 items-center gap-3">
      <span class="w-32 shrink-0 overflow-hidden rounded-md border border-default bg-elevated sm:w-36" aria-hidden="true">
        <PageDesignsThumb :tokens="page.tokens" />
      </span>
      <div class="flex min-w-0 flex-1 flex-col gap-1">
        <NuxtLink
          :to="`/settings/landing-pages/${page.id}`"
          class="line-clamp-2 text-base leading-snug font-semibold text-highlighted hover:underline focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
          >{{ name }}</NuxtLink
        >
        <p class="flex min-w-0 items-center gap-1.5 text-sm text-muted">
          <UIcon name="i-lucide-panels-top-left" class="size-3.5 shrink-0" />
          <span class="truncate">{{ t(`designer.frame.style.${page.tokens.frame.style}`) }} · {{ t(`designer.frame.toneValue.${page.tokens.frame.tone}`) }}</span>
        </p>
      </div>
    </div>

    <!-- Buttons: Changed · kind · menu -->
    <div class="mt-auto flex items-center justify-between gap-2 border-t border-default pt-3">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon :name="busy ? 'i-lucide-loader-circle' : 'i-lucide-clock-3'" class="size-3.5 shrink-0 text-muted" :class="busy ? 'animate-spin' : ''" />
        <span class="truncate">{{ t('themes.card.changed', { when: relative(page.updated_at) }) }}</span>
      </span>
      <div class="flex min-w-0 items-center gap-1.5">
        <UBadge :label="t(`themes.source.${page.source}`)" :icon="SOURCE_ICON[page.source]" color="neutral" variant="outline" size="sm" class="min-w-0 truncate" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <!-- Details (two columns, one line each) -->
    <dl class="grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm" :class="fact.key === 'forms' ? 'font-medium text-highlighted tabular-nums' : 'text-default'">{{ fact.value }}</dd>
      </div>
    </dl>
  </article>
</template>
