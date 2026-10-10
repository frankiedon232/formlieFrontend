<!-- A list of help articles (F25): area icon, title, summary (or a search snippet), minutes to read. -->
<script setup lang="ts">
import type { HelpArticleSummary } from '#shared/types/help'
import { HELP_CATEGORY_ICONS, helpArticlePath } from '#shared/utils/help/categories'

/** compact: title only (side columns). */
defineProps<{ articles: (HelpArticleSummary & { snippet?: string })[]; showArea?: boolean; compact?: boolean }>()
const { t } = useI18n()
</script>

<template>
  <ul class="flex flex-col divide-y divide-default">
    <li v-for="article in articles" :key="article.id">
      <NuxtLink :to="helpArticlePath(article)" class="flex items-start gap-3 rounded-md px-1 py-3 hover:bg-elevated/50 focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
        <span class="flex size-8 shrink-0 items-center justify-center rounded-lg border border-default"><UIcon :name="HELP_CATEGORY_ICONS[article.category]" class="size-4 text-muted" /></span>
        <span class="flex min-w-0 flex-1 flex-col gap-0.5">
          <span class="text-sm font-medium text-highlighted">{{ article.title }}</span>
          <span v-if="!compact" class="line-clamp-2 text-xs text-muted">{{ article.snippet ?? article.summary }}</span>
        </span>
        <span v-if="!compact" class="flex shrink-0 flex-col items-end gap-1 text-[11px] text-muted">
          <span class="tabular-nums">{{ t('help.minutes', { n: article.minutes }, article.minutes) }}</span>
          <span v-if="showArea">{{ t(`help.category.${article.category}.name`) }}</span>
        </span>
      </NuxtLink>
    </li>
  </ul>
</template>
