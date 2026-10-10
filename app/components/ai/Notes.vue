<!-- What the assistant did (F19): its notes, translated, with a "Made with AI" mark. -->
<script setup lang="ts">
import type { AiDraftStats, AiNote } from '#shared/types/ai'

defineProps<{ notes: AiNote[]; stats?: AiDraftStats | null }>()
const { t, d } = useI18n()
/** A note's values, with a theme's name and a day in the reader's language. */
const paramsOf = (note: AiNote) => ({
  ...note.params,
  ...(note.theme ? { theme: t(`ai.theme.${note.theme}`) } : {}),
  ...(typeof note.params?.day === 'string' ? { day: d(new Date(`${note.params.day}T12:00:00`), { weekday: 'long', day: 'numeric', month: 'long' }) } : {}),
})
</script>

<template>
  <div class="flex flex-col gap-2">
    <div v-if="stats" class="flex flex-wrap items-center gap-1.5">
      <UBadge :label="t('ai.label.made')" icon="i-lucide-sparkles" color="neutral" variant="soft" size="sm" class="rounded-md" />
      <UBadge :label="t('ai.stats.pages', { n: stats.pages }, stats.pages)" icon="i-lucide-files" color="neutral" variant="outline" size="sm" class="rounded-md" />
      <UBadge :label="t('ai.stats.fields', { n: stats.fields }, stats.fields)" icon="i-lucide-list" color="neutral" variant="outline" size="sm" class="rounded-md" />
      <UBadge v-if="stats.logic" :label="t('ai.stats.logic', { n: stats.logic }, stats.logic)" icon="i-lucide-git-branch" color="neutral" variant="outline" size="sm" class="rounded-md" />
      <UBadge v-if="stats.calculations" :label="t('ai.stats.calculations', { n: stats.calculations }, stats.calculations)" icon="i-lucide-calculator" color="neutral" variant="outline" size="sm" class="rounded-md" />
    </div>
    <ul v-if="notes.length" class="flex flex-col gap-1.5">
      <li v-for="(note, index) in notes" :key="index" class="flex items-start gap-2 text-sm text-muted">
        <UIcon name="i-lucide-sparkle" class="mt-0.5 size-3.5 shrink-0 text-default" />
        <span>{{ t(`ai.note.${note.code}`, paramsOf(note), typeof note.params?.n === 'number' ? note.params.n : 1) }}</span>
      </li>
    </ul>
  </div>
</template>
