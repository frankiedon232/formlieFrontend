<!--
  An export on Responses → Exports (F11 M3), in the locked card format (rule 21): a "made" pill,
  the file's state and ⋯ on top; the file name (format icon) and its form; responses, columns,
  which responses and size in two columns; a divider, then "Available" with a black bar for the
  part of its 7 days left (or the progress while it is being made); author, format and download.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ResponseExport } from '#shared/types/responses'

const props = defineProps<{ item: ResponseExport; actions: DropdownMenuItem[][]; busy?: boolean }>()
const emit = defineEmits<{ download: [] }>()
const { t } = useI18n()
const { relative, number, fileSize } = useFormat()
const ICON = { xlsx: 'i-lucide-file-spreadsheet', csv: 'i-lucide-file-text', pdf: 'i-lucide-file-type' } as const
const KEEP = 7 * 24 * 60 * 60 * 1000
const working = computed(() => props.item.status === 'queued' || props.item.status === 'running')
const left = computed(() => Math.max(0, Math.min(1, (Date.parse(props.item.expires_at) - Date.now()) / KEEP)))
const facts = computed(() => [
  { key: 'rows', label: t('responses.exports.col.rows'), value: t('responses.export.rows', { n: number(props.item.rows) }, props.item.rows) },
  { key: 'columns', label: t('responses.exports.col.columns'), value: number(props.item.columns) },
  { key: 'scope', label: t('responses.exports.col.scope'), value: t(`responses.exports.scope.${props.item.scope}`) },
  { key: 'size', label: t('responses.exports.col.size'), value: props.item.size ? fileSize(props.item.size) : '–' },
])
</script>

<template>
  <article class="group flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md">
    <!-- Made · state · menu -->
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon :name="busy || working ? 'i-lucide-loader-circle' : 'i-lucide-clock-3'" class="size-3.5 shrink-0 text-muted" :class="busy || working ? 'animate-spin' : ''" />
        <span class="truncate">{{ t('responses.exports.made', { when: relative(item.created_at) }) }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <DataStatusBadge :status="item.status" :label="t(`responses.exports.status.${item.status}`)" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <!-- File and form -->
    <div class="mt-3 flex min-w-0 items-center gap-1.5">
      <UIcon :name="ICON[item.format]" class="size-4 shrink-0 text-muted" />
      <span class="truncate text-base font-semibold text-highlighted">{{ item.file_name }}</span>
    </div>
    <NuxtLink :to="`/forms/${item.form.id}/responses`" class="flex min-w-0 items-center gap-1.5 text-sm text-muted hover:underline">
      <UIcon name="i-lucide-file-text" class="size-3.5 shrink-0" />
      <span class="truncate">{{ item.form.name }}</span>
    </NuxtLink>

    <!-- Facts (two columns, one line each) -->
    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm tabular-nums" :class="fact.key === 'rows' ? 'font-medium text-highlighted' : 'text-default'">{{ fact.value }}</dd>
      </div>
    </dl>

    <!-- Available (the design's Progress) -->
    <div class="mt-auto pt-4">
      <div class="border-t border-default pt-3">
        <div class="mb-1.5 flex items-center justify-between text-xs">
          <span class="text-muted">{{ working ? t('responses.export.making') : t('responses.exports.available') }}</span>
          <span class="font-medium text-highlighted tabular-nums">{{ working ? `${item.progress}%` : item.status === 'expired' ? t('responses.exports.status.expired') : relative(item.expires_at) }}</span>
        </div>
        <div class="h-1.5 overflow-hidden rounded-full bg-elevated" role="presentation">
          <div class="h-full rounded-full bg-inverted transition-[width]" :style="{ width: `${(working ? item.progress / 100 : left) * 100}%` }" />
        </div>
      </div>

      <!-- Author, format, download -->
      <div class="mt-4 flex items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-2">
          <UAvatar :alt="item.created_by.name" size="xs" />
          <span class="truncate text-xs text-muted">{{ item.created_by.name }}</span>
        </div>
        <UButton
          v-if="item.status === 'ready'"
          :label="t('responses.export.download')"
          icon="i-lucide-download"
          color="neutral"
          variant="outline"
          size="xs"
          :loading="busy"
          @click="emit('download')"
        />
        <UBadge v-else :label="t(`responses.export.format.${item.format}`)" color="neutral" variant="outline" size="sm" />
      </div>
    </div>
  </article>
</template>
