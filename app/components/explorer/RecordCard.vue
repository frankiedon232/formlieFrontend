<!--
  A row as a card (grid view, locked card format, rule 21): its key as a pill and the first text
  column as the title, then the next values in two columns, one line each. The card opens the row.
-->
<script setup lang="ts">
import type { TableRow, TableStructure } from '#shared/types/explorer'

const props = defineProps<{ row: TableRow; structure: TableStructure; columns: string[] }>()
const { t } = useI18n()
const titleColumn = computed(() => props.structure.columns.find(column => !column.primary && /CHAR|TEXT|CLOB/i.test(column.type) && typeof props.row[column.name] === 'string')?.name ?? null)
const facts = computed(() => props.columns.filter(name => name !== titleColumn.value && !props.structure.primary_key.includes(name)).slice(0, 6))
</script>

<template>
  <article class="flex h-full flex-col gap-3 rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md">
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 font-mono text-xs text-toned" dir="ltr">
        <UIcon name="i-lucide-key-round" class="size-3.5 shrink-0 text-muted" />
        <span class="truncate">{{ row.__key }}</span>
      </span>
    </div>
    <p class="truncate text-base font-semibold text-highlighted" dir="auto">{{ titleColumn ? row[titleColumn] : t('explorer.row', { key: row.__key }) }}</p>
    <dl class="grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="name in facts" :key="name" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate font-mono text-[11px] text-muted" dir="ltr">{{ name }}</dt>
        <dd class="h-5 truncate text-sm"><ExplorerCell :value="row[name]" /></dd>
      </div>
    </dl>
  </article>
</template>
