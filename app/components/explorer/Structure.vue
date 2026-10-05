<!--
  A table's structure (F12 M3): columns with type, nullability, default and key marks; indexes;
  relations to other tables (each opens that table); and the definition, with Copy. On the
  organisation's own tables with Full access (`alterable`, never response tables): Add column,
  each column's ⋯ (Edit, Delete; key columns only rename), Add index and Delete index.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ExplorerColumn, TableIndex, TableStructure } from '#shared/types/explorer'

const props = defineProps<{ structure: TableStructure; removing?: string | null }>()
const emit = defineEmits<{
  table: [ref: { schema: string; table: string }]
  addColumn: []
  editColumn: [column: ExplorerColumn]
  dropColumn: [column: ExplorerColumn]
  addIndex: []
  dropIndex: [index: TableIndex]
}>()
const { t } = useI18n()
const toast = useToast()
const { copy } = useClipboard({ legacy: true })
const columnMenu = (column: ExplorerColumn): DropdownMenuItem[][] => [
  [{ label: column.primary ? t('explorer.ddl.renameColumn') : t('explorer.ddl.editColumnShort'), icon: 'i-lucide-pencil', onSelect: () => emit('editColumn', column) }],
  ...(column.primary || props.structure.columns.length === 1 ? [] : [[{ label: t('explorer.ddl.dropColumn'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => emit('dropColumn', column) }]]),
]
function copyDdl() {
  void copy(props.structure.ddl)
  toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
}
</script>

<template>
  <div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
    <section class="flex flex-col gap-2 xl:col-span-2">
      <div class="flex items-center justify-between gap-2">
        <h3 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('explorer.structure.columns', { n: structure.columns.length }) }}</h3>
        <UButton v-if="structure.alterable" :label="t('explorer.ddl.addColumn')" icon="i-lucide-plus" color="neutral" variant="outline" size="xs" @click="emit('addColumn')" />
      </div>
      <div class="overflow-x-auto rounded-lg border border-default">
        <table class="w-full text-sm">
          <thead class="bg-elevated/50 text-xs text-muted">
            <tr>
              <th class="px-3 py-2 text-start font-medium">{{ t('explorer.structure.name') }}</th>
              <th class="px-3 py-2 text-start font-medium">{{ t('explorer.structure.type') }}</th>
              <th class="px-3 py-2 text-start font-medium">{{ t('explorer.structure.nullable') }}</th>
              <th class="hidden px-3 py-2 text-start font-medium md:table-cell">{{ t('explorer.structure.default') }}</th>
              <th class="px-3 py-2 text-start font-medium">{{ t('explorer.structure.keys') }}</th>
              <th v-if="structure.alterable" class="w-10 px-2 py-2"><span class="sr-only">{{ t('explorer.ddl.actions') }}</span></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-default">
            <tr v-for="column in structure.columns" :key="column.name" :class="removing === column.name ? 'pointer-events-none animate-pulse opacity-60' : ''">
              <td class="px-3 py-2 font-mono text-xs text-highlighted" dir="ltr">{{ column.name }}</td>
              <td class="px-3 py-2 font-mono text-xs text-default" dir="ltr">{{ column.type }}</td>
              <td class="px-3 py-2 text-xs" :class="column.nullable ? 'text-muted' : 'text-highlighted'">{{ column.nullable ? t('dataSources.yes') : t('dataSources.no') }}</td>
              <td class="hidden px-3 py-2 font-mono text-xs text-muted md:table-cell" dir="ltr">{{ column.default ?? '–' }}</td>
              <td class="px-3 py-2">
                <div class="flex flex-wrap gap-1">
                  <UBadge v-if="column.primary" :label="t('explorer.structure.pk')" color="neutral" size="sm" class="rounded-md" />
                  <UBadge v-else-if="column.unique" :label="t('explorer.structure.unique')" color="neutral" variant="outline" size="sm" class="rounded-md" />
                  <UBadge v-if="column.references" :label="t('explorer.structure.fk')" color="neutral" variant="soft" size="sm" class="rounded-md" />
                </div>
              </td>
              <td v-if="structure.alterable" class="px-2 py-1 text-end">
                <UDropdownMenu :items="columnMenu(column)" :content="{ align: 'end' }">
                  <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="xs" square :loading="removing === column.name" :aria-label="t('explorer.ddl.columnActions', { column: column.name })" />
                </UDropdownMenu>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="flex flex-col gap-2">
      <div class="flex items-center justify-between gap-2">
        <h3 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('explorer.structure.indexes') }}</h3>
        <UButton v-if="structure.alterable" :label="t('explorer.ddl.addIndex')" icon="i-lucide-plus" color="neutral" variant="outline" size="xs" @click="emit('addIndex')" />
      </div>
      <ul v-if="structure.indexes.length" class="divide-y divide-default rounded-lg border border-default">
        <li v-for="index in structure.indexes" :key="index.name" class="flex flex-wrap items-center gap-2 px-3 py-2 text-sm" :class="removing === index.name ? 'animate-pulse opacity-60' : ''">
          <code class="min-w-0 flex-1 truncate font-mono text-xs text-highlighted" dir="ltr">{{ index.name }}</code>
          <code class="font-mono text-xs text-muted" dir="ltr">({{ index.columns.join(', ') }})</code>
          <UBadge v-if="index.primary" :label="t('explorer.structure.pk')" color="neutral" size="sm" class="rounded-md" />
          <UBadge v-else-if="index.unique" :label="t('explorer.structure.unique')" color="neutral" variant="outline" size="sm" class="rounded-md" />
          <UButton v-if="structure.alterable && !index.primary" icon="i-lucide-trash-2" color="neutral" variant="ghost" size="xs" square :loading="removing === index.name" :aria-label="t('explorer.ddl.dropIndexNamed', { index: index.name })" @click="emit('dropIndex', index)" />
        </li>
      </ul>
      <p v-else class="text-sm text-muted">{{ t('explorer.structure.noIndexes') }}</p>
    </section>

    <section class="flex flex-col gap-2">
      <h3 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('explorer.structure.relations') }}</h3>
      <ul v-if="structure.foreign_keys.length" class="divide-y divide-default rounded-lg border border-default">
        <li v-for="key in structure.foreign_keys" :key="key.name" class="flex flex-wrap items-center gap-2 px-3 py-2 text-sm">
          <code class="font-mono text-xs text-highlighted" dir="ltr">{{ key.columns.join(', ') }}</code>
          <UIcon name="i-lucide-arrow-right" class="size-3.5 text-muted rtl:-scale-x-100" />
          <UButton :label="`${key.references.schema}.${key.references.table} (${key.references.columns.join(', ')})`" color="neutral" variant="link" size="xs" class="px-0 font-mono" @click="emit('table', { schema: key.references.schema, table: key.references.table })" />
        </li>
      </ul>
      <p v-else class="text-sm text-muted">{{ t('explorer.structure.noRelations') }}</p>
    </section>

    <section class="flex flex-col gap-2 xl:col-span-2">
      <div class="flex items-center justify-between gap-2">
        <h3 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('explorer.structure.definition') }}</h3>
        <UButton :label="t('common.copy')" icon="i-lucide-copy" color="neutral" variant="outline" size="xs" @click="copyDdl" />
      </div>
      <pre class="max-h-96 overflow-auto rounded-lg border border-default px-3 py-2.5 font-mono text-[11px] leading-relaxed text-default" dir="ltr" tabindex="0">{{ structure.ddl }}</pre>
    </section>
  </div>
</template>
