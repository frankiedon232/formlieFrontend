<!--
  Step 5: a summary (each line jumps back to its step) and exactly what Formalie will run on the
  database when saved: the CREATE TABLE for a new table, or the columns and unique key it adds to
  a table of theirs. Nothing runs before Save.
-->
<script setup lang="ts">
import { addColumnSql, createTableSql, uniqueKeySql } from '#shared/utils/datasources/tables'

const props = defineProps<{ setup: ReturnType<typeof useStorageSetup>; editing: boolean }>()
const emit = defineEmits<{ jump: [step: string] }>()
const { t } = useI18n()
const toast = useToast()
const { copy } = useClipboard({ legacy: true })
const s = props.setup

const target = computed(() => (s.mode.value === 'create' ? { schema: s.tablesSchema.value, name: s.tableName.value.trim() } : s.existing.value ? { schema: s.existing.value.schema, name: s.existing.value.name } : null))
const sql = computed(() => {
  const engine = s.engine.value
  const table = target.value
  if (!engine || !table) return ''
  if (s.mode.value === 'create' && !props.editing) return createTableSql(engine, table.schema, table.name, s.columns.value)
  const statements = s.columns.value.filter(column => !column.existing).map(column => addColumnSql(engine, table.schema, table.name, column))
  const keyColumn = s.existing.value?.columns.find(column => column.name === s.settings.value.key_column)
  if (s.settings.value.write_mode === 'upsert' && keyColumn && !keyColumn.unique && !keyColumn.primary) statements.push(uniqueKeySql(engine, table.schema, table.name, keyColumn.name))
  return statements.join('\n')
})
const filled = computed(() => s.columns.value.filter(column => column.source).length)
const rows = computed(() => [
  { key: 'connection', step: 'connection', icon: s.engine.value ? engineIcon(s.engine.value) : 'i-lucide-database', label: t('destinations.setup.step.connection'), value: s.source.value?.name ?? '' },
  { key: 'table', step: 'table', icon: 'i-lucide-table-2', label: t('destinations.setup.step.table'), value: target.value ? `${target.value.schema}.${target.value.name}` : '', ltr: true },
  { key: 'columns', step: 'columns', icon: 'i-lucide-columns-3', label: t('destinations.setup.step.columns'), value: t('destinations.setup.columnsCount', { filled: filled.value, total: s.columns.value.length }) },
  { key: 'write', step: 'options', icon: 'i-lucide-pencil-line', label: t('destinations.options.writeLegend'), value: t(`destinations.options.write.${s.settings.value.write_mode}`) },
])
function copySql() {
  void copy(sql.value)
  toast.add({ title: t('dataSources.grant.copied'), color: 'success', icon: 'i-lucide-check' })
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <dl class="grid grid-cols-1 gap-2 sm:grid-cols-2">
      <button
        v-for="row in rows"
        :key="row.key"
        type="button"
        class="flex min-w-0 items-center gap-2.5 rounded-lg border border-default px-3 py-2 text-start transition hover:border-accented hover:bg-elevated/40 focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
        :aria-label="t('dataSources.summary.change', { item: row.label })"
        @click="emit('jump', row.step)"
      >
        <UIcon :name="row.icon" class="size-4 shrink-0 text-muted" />
        <span class="flex min-w-0 flex-1 flex-col">
          <dt class="text-[11px] text-muted">{{ row.label }}</dt>
          <dd class="truncate text-sm font-medium text-highlighted" :class="row.ltr ? 'text-start font-mono text-xs' : ''" :dir="row.ltr ? 'ltr' : undefined">{{ row.value || '–' }}</dd>
        </span>
        <UIcon name="i-lucide-pencil" class="size-3.5 shrink-0 text-dimmed" />
      </button>
    </dl>

    <section class="overflow-hidden rounded-lg border border-default">
      <header class="flex items-center justify-between gap-2 bg-elevated/50 px-3 py-1.5">
        <h3 class="text-xs font-semibold text-highlighted">{{ sql ? t('destinations.setup.sqlTitle') : t('destinations.setup.sqlNone') }}</h3>
        <UButton v-if="sql" icon="i-lucide-copy" color="neutral" variant="ghost" size="xs" :aria-label="t('common.copy')" @click="copySql" />
      </header>
      <pre v-if="sql" class="max-h-80 overflow-auto px-3 py-2.5 font-mono text-[11px] leading-relaxed text-default" dir="ltr" tabindex="0">{{ sql }}</pre>
      <p class="flex gap-1.5 border-t border-default px-3 py-2 text-xs text-muted">
        <UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" />
        {{ sql ? t('destinations.setup.sqlNote') : t('destinations.setup.sqlNoneNote') }}
      </p>
    </section>
  </div>
</template>
