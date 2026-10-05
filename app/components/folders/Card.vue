<!--
  A folder on the Folders page (F11 M4; locked card format, rule 21): a "last activity" pill and ⋯
  on top; the folder (in its colour) and how many forms; published, drafts, responses in the last
  30 days and all time in two columns; a divider, then Completion with a black bar; the owners and
  a 30-day sparkline at the bottom. The whole card opens the folder.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { FolderRow } from '#shared/types/forms'
import { folderColor } from '#shared/utils/forms/folders'

const props = defineProps<{ folder: FolderRow; actions: DropdownMenuItem[][] }>()
const { t } = useI18n()
const { relative, number } = useFormat()
const facts = computed(() => [
  { key: 'published', label: t('status.published'), value: number(props.folder.status_counts.published) },
  { key: 'draft', label: t('status.draft'), value: number(props.folder.status_counts.draft) },
  { key: 'recent', label: t('folders.responses30'), value: number(props.folder.responses_30d) },
  { key: 'total', label: t('responses.kpi.totalLabel'), value: number(props.folder.responses_count) },
])
</script>

<template>
  <article class="group flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md">
    <!-- Last activity · menu -->
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon name="i-lucide-clock-3" class="size-3.5 shrink-0 text-muted" />
        <span class="truncate">{{ folder.last_activity_at ? t('folders.active', { when: relative(folder.last_activity_at) }) : t('folders.noActivity') }}</span>
      </span>
      <UDropdownMenu :items="actions" :content="{ align: 'end' }">
        <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
      </UDropdownMenu>
    </div>

    <!-- Folder and forms -->
    <div class="mt-3 flex min-w-0 items-center gap-2">
      <UIcon name="i-lucide-folder" class="size-5 shrink-0" :class="folderColor(folder.color).text" />
      <NuxtLink :to="`/folders/${folder.id}`" class="truncate text-base font-semibold text-highlighted hover:underline focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">{{ folder.name }}</NuxtLink>
    </div>
    <p class="text-sm text-muted">{{ t('forms.folders.count', { count: folder.forms_count }, folder.forms_count) }}</p>

    <!-- Facts (two columns, one line each) -->
    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm tabular-nums" :class="fact.key === 'recent' ? 'font-medium text-highlighted' : 'text-default'">{{ fact.value }}</dd>
      </div>
    </dl>

    <!-- Completion (the design's Progress) -->
    <div class="mt-auto pt-4">
      <div class="border-t border-default pt-3">
        <div class="mb-1.5 flex items-center justify-between text-xs">
          <span class="text-muted">{{ t('forms.col.completion') }}</span>
          <span class="font-medium text-highlighted tabular-nums">{{ folder.completion_rate === null ? '–' : `${folder.completion_rate}%` }}</span>
        </div>
        <div class="h-1.5 overflow-hidden rounded-full bg-elevated" role="presentation">
          <div class="h-full rounded-full bg-inverted" :style="{ width: `${folder.completion_rate ?? 0}%` }" />
        </div>
      </div>

      <!-- Owners, trend -->
      <div class="mt-4 flex items-center justify-between gap-2">
        <UAvatarGroup v-if="folder.owners.length" size="xs" :max="4">
          <UAvatar v-for="owner in folder.owners" :key="owner.id" :alt="owner.name" />
        </UAvatarGroup>
        <span v-else class="text-xs text-muted">{{ t('folders.empty') }}</span>
        <ChartsSparkline :values="folder.daily.map(day => day.count)" :width="72" :height="20" />
      </div>
    </div>
  </article>
</template>
