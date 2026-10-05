<!--
  A table's structure (F12 M3, read only): columns with type, nullability, default and key marks;
  indexes; relations to other tables (each opens that table); and the definition, with Copy.
-->
<script setup lang="ts">
import type { TableStructure } from '#shared/types/explorer'

const props = defineProps<{ structure: TableStructure }>()
const emit = defineEmits<{ table: [ref: { schema: string; table: string }] }>()
const { t } = useI18n()
const toast = useToast()
const { copy } = useClipboard({ legacy: true })
function copyDdl() {
  void copy(props.structure.ddl)
  toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
}
</script>

<template>
  <div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
    <section class="flex flex-col gap-2 xl:col-span-2">
      <h3 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('explorer.structure.columns', { n: structure.columns.length }) }}</h3>
      <div class="overflow-x-auto rounded-lg border border-default">
        <table class="w-full text-sm">
          <thead class="bg-elevated/50 text-xs text-muted">
            <tr>
              <th class="px-3 py-2 text-start font-medium">{{ t('explorer.structure.name') }}</th>
              <th class="px-3 py-2 text-start font-medium">{{ t('explorer.structure.type') }}</th>
              <th class="px-3 py-2 text-start font-medium">{{ t('explorer.structure.nullable') }}</th>
              <th class="hidden px-3 py-2 text-start font-medium md:table-cell">{{ t('explorer.structure.default') }}</th>
              <th class="px-3 py-2 text-start font-medium">{{ t('explorer.structure.keys') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-default">
            <tr v-for="column in structure.columns" :key="column.name">
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
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="flex flex-col gap-2">
      <h3 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('explorer.structure.indexes') }}</h3>
      <ul v-if="structure.indexes.length" class="divide-y divide-default rounded-lg border border-default">
        <li v-for="index in structure.indexes" :key="index.name" class="flex flex-wrap items-center gap-2 px-3 py-2 text-sm">
          <code class="min-w-0 flex-1 truncate font-mono text-xs text-highlighted" dir="ltr">{{ index.name }}</code>
          <code class="font-mono text-xs text-muted" dir="ltr">({{ index.columns.join(', ') }})</code>
          <UBadge v-if="index.primary" :label="t('explorer.structure.pk')" color="neutral" size="sm" class="rounded-md" />
          <UBadge v-else-if="index.unique" :label="t('explorer.structure.unique')" color="neutral" variant="outline" size="sm" class="rounded-md" />
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
