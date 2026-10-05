<!--
  Create a table in the organisation's database (F12 M3; Full access). Schema, name (a letter
  first, letters, numbers and underscores; Formalie's prefixes are kept for its own tables), its
  columns (starts with a numbered key and one text column), and the exact CREATE TABLE that will
  run. Opens the new table when done.
-->
<script setup lang="ts">
import { checkName, createTableStatements, normaliseName, type ColumnSpec } from '#shared/utils/datasources/ddl'
import type { DbEngine } from '#shared/utils/integrations/databases'

const props = defineProps<{ sourceId: string; engine: DbEngine; schemas: string[] }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ created: [table: { schema: string; name: string }] }>()
const { t } = useI18n()
const { busy, errors, create } = useSchemaChange()

const upper = computed(() => props.engine === 'oracle')
const starter = (): ColumnSpec[] => [
  { name: upper.value ? 'ID' : 'id', kind: 'big_integer', nullable: false, primary: true, auto: true },
  { name: upper.value ? 'NAME' : 'name', kind: 'text', length: 200, nullable: true },
]
const schema = ref('')
const name = ref('')
const columns = ref<ColumnSpec[]>(starter())
watch(open, isOpen => {
  if (!isOpen) return
  schema.value = props.schemas[0] ?? ''
  name.value = ''
  columns.value = starter()
  errors.value = {}
})

const statements = computed(() => (name.value && columns.value.length ? createTableStatements(props.engine, schema.value, name.value, columns.value) : []))
const columnErrors = (index: number) => Object.fromEntries(Object.entries(errors.value).filter(([key]) => key.startsWith(`columns.${index}.`)).map(([key, value]) => [key.split('.').pop()!, value]))
function addColumn() {
  columns.value = [...columns.value, { name: '', kind: 'text', length: 200, nullable: true }]
}
const removeColumn = (index: number) => (columns.value = columns.value.filter((_, i) => i !== index))

async function submit() {
  name.value = normaliseName(props.engine, name.value)
  const problem = checkName(props.engine, name.value, 'table')
  const local: Record<string, string> = {}
  if (problem) local.name = t(`explorer.ddl.problem.${problem}`)
  columns.value.forEach((column, index) => {
    const columnProblem = checkName(props.engine, column.name, 'column')
    if (columnProblem) local[`columns.${index}.name`] = t(`explorer.ddl.problem.${columnProblem}`)
  })
  errors.value = local
  if (Object.keys(local).length) return
  const result = await create(props.sourceId, schema.value, name.value, columns.value)
  if (!result?.table) return
  useToast().add({ title: t('explorer.ddl.created', { table: result.table.name }), color: 'success', icon: 'i-lucide-circle-check' })
  open.value = false
  emit('created', result.table)
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="t('explorer.ddl.newTable')" :description="t('explorer.ddl.newTableDesc')" :dismissible="!busy" :ui="{ content: 'sm:max-w-3xl' }">
    <template #body>
      <form id="new-table" class="flex flex-col gap-4" novalidate @submit.prevent="submit">
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
          <UFormField :label="t('explorer.ddl.schema')" :error="errors.schema">
            <USelect v-model="schema" :items="schemas" class="w-full font-mono" />
          </UFormField>
          <UFormField :label="t('explorer.ddl.tableName')" :error="errors.name" required>
            <UInput v-model="name" autofocus class="w-full font-mono" dir="ltr" :placeholder="upper ? 'SUPPLIER_CONTACTS' : 'supplier_contacts'" @blur="name = normaliseName(engine, name)" />
          </UFormField>
        </div>
        <section class="flex flex-col gap-2">
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('explorer.ddl.columns', { n: columns.length }) }}</h3>
            <UButton :label="t('explorer.ddl.addColumn')" icon="i-lucide-plus" color="neutral" variant="outline" size="xs" @click="addColumn" />
          </div>
          <ol class="flex flex-col gap-2">
            <li v-for="(column, index) in columns" :key="index" class="relative rounded-lg border border-default p-3 pe-10">
              <ExplorerColumnFields v-model="columns[index]!" :engine="engine" :errors="columnErrors(index)" new-table compact />
              <UButton v-if="columns.length > 1" icon="i-lucide-x" color="neutral" variant="ghost" size="xs" square class="absolute end-2 top-2" :aria-label="t('explorer.ddl.removeColumn', { column: column.name || index + 1 })" @click="removeColumn(index)" />
            </li>
          </ol>
        </section>
        <ExplorerSqlPreview :statements="statements" />
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" :disabled="busy" @click="open = false" />
        <UButton type="submit" form="new-table" :label="t('explorer.ddl.create')" icon="i-lucide-table-2" color="neutral" :loading="busy" />
      </div>
    </template>
  </AppModal>
</template>
