<!--
  Add a column to, or change a column of, the organisation's own table (F12 M3). Shows the exact
  statements first; a change that may lose or refuse data (a shorter text, another kind) says so.
  Key columns only change their name. A new column that can't be empty needs a default when the
  table already has rows.
-->
<script setup lang="ts">
import type { ExplorerColumn, SchemaResult, TableStructure } from '#shared/types/explorer'
import { changeStatements, checkName, normaliseName, specOfType, typeChangeRisky, type ColumnSpec, type TableChange } from '#shared/utils/datasources/ddl'
import type { DbEngine } from '#shared/utils/integrations/databases'

const props = defineProps<{ sourceId: string; engine: DbEngine; structure: TableStructure; column: ExplorerColumn | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ done: [result: SchemaResult] }>()
const { t } = useI18n()
const { busy, errors, change } = useSchemaChange()

const spec = ref<ColumnSpec>({ name: '', kind: 'text', length: 200, nullable: true })
watch(open, isOpen => {
  if (!isOpen) return
  errors.value = {}
  const column = props.column
  spec.value = column ? { name: column.name, ...specOfType(column.type), nullable: column.nullable, default: column.primary ? null : column.default, primary: column.primary } : { name: '', kind: 'text', length: 200, nullable: true }
})

const step = computed<TableChange>(() => (props.column ? { op: 'alter_column', column: props.column.name, to: spec.value } : { op: 'add_column', column: spec.value }))
const current = computed(() => (props.column ? { name: props.column.name, type: props.column.type, nullable: props.column.nullable, default: props.column.primary ? null : props.column.default, primary: props.column.primary } : undefined))
const statements = computed(() => (spec.value.name ? changeStatements(props.engine, props.structure.schema, props.structure.name, step.value, current.value) : []))
const risky = computed(() => !!props.column && !props.column.primary && typeChangeRisky(props.column.type, spec.value))
const fieldErrors = computed(() => Object.fromEntries(Object.entries(errors.value).map(([key, value]) => [key.split('.').pop()!, value])))

async function submit() {
  spec.value = { ...spec.value, name: normaliseName(props.engine, spec.value.name) }
  const problem = checkName(props.engine, spec.value.name, 'column')
  if (problem) return void (errors.value = { name: t(`explorer.ddl.problem.${problem}`) })
  if (props.column && !statements.value.length) return void (open.value = false)
  const result = await change(props.sourceId, props.structure.schema, props.structure.name, step.value)
  if (!result) return
  useToast().add({ title: props.column ? t('explorer.ddl.columnChanged', { column: spec.value.name }) : t('explorer.ddl.columnAdded', { column: spec.value.name }), color: 'success', icon: 'i-lucide-circle-check' })
  open.value = false
  emit('done', result)
}
</script>

<template>
  <AppModal
    v-model:open="open"
    :title="column ? t('explorer.ddl.editColumn', { column: column.name }) : t('explorer.ddl.addColumn')"
    :description="`${structure.schema}.${structure.name}`"
    :dismissible="!busy"
    :ui="{ content: 'sm:max-w-2xl' }"
  >
    <template #body>
      <form id="column-form" class="flex flex-col gap-4" novalidate @submit.prevent="submit">
        <ExplorerColumnFields v-model="spec" :engine="engine" :errors="fieldErrors" :key-column="column?.primary" />
        <UAlert v-if="risky" icon="i-lucide-triangle-alert" color="warning" variant="subtle" :title="t('explorer.ddl.riskyTitle')" :description="t('explorer.ddl.riskyDesc')" />
        <ExplorerSqlPreview :statements="statements" />
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" :disabled="busy" @click="open = false" />
        <UButton type="submit" form="column-form" :label="column ? t('common.save') : t('explorer.ddl.addColumn')" icon="i-lucide-check" color="neutral" :loading="busy" />
      </div>
    </template>
  </AppModal>
</template>
