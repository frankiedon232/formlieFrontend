<!--
  Structure changes for one of the organisation's own tables (F12 M3; Full access, never response
  tables): the dialogs for columns, indexes, renaming, emptying and deleting, opened by the table
  menu and the Structure tab. Deleting a column or an index asks first. Emits the server's answer
  so the page reloads what changed.
-->
<script setup lang="ts">
import type { ExplorerColumn, SchemaResult, TableIndex, TableStructure } from '#shared/types/explorer'
import type { DbEngine } from '#shared/utils/integrations/databases'

const props = defineProps<{ sourceId: string; engine: DbEngine; structure: TableStructure }>()
const emit = defineEmits<{ changed: [result: SchemaResult] }>()
const { t } = useI18n()
const confirm = useConfirm()
const { change } = useSchemaChange()

const columnOpen = ref(false)
const column = ref<ExplorerColumn | null>(null)
const indexOpen = ref(false)
const tableOpen = ref(false)
const tableMode = ref<'rename' | 'truncate' | 'drop'>('rename')
/** The column or index being deleted (its row shows busy). */
const removing = ref<string | null>(null)

function editColumn(item: ExplorerColumn | null) {
  column.value = item
  columnOpen.value = true
}
function table(mode: 'rename' | 'truncate' | 'drop') {
  tableMode.value = mode
  tableOpen.value = true
}
async function dropColumn(item: ExplorerColumn) {
  if (!(await confirm({ title: t('explorer.ddl.dropColumnTitle', { column: item.name }), description: t('explorer.ddl.dropColumnDesc'), confirmLabel: t('explorer.ddl.dropColumn'), danger: true }))) return
  removing.value = item.name
  try {
    const result = await change(props.sourceId, props.structure.schema, props.structure.name, { op: 'drop_column', column: item.name })
    if (!result) return
    useToast().add({ title: t('explorer.ddl.columnDropped', { column: item.name }), color: 'success', icon: 'i-lucide-circle-check' })
    emit('changed', result)
  } finally {
    removing.value = null
  }
}
async function dropIndex(item: TableIndex) {
  if (!(await confirm({ title: t('explorer.ddl.dropIndexTitle', { index: item.name }), description: t('explorer.ddl.dropIndexDesc'), confirmLabel: t('explorer.ddl.dropIndex'), danger: true }))) return
  removing.value = item.name
  try {
    const result = await change(props.sourceId, props.structure.schema, props.structure.name, { op: 'drop_index', name: item.name })
    if (!result) return
    useToast().add({ title: t('explorer.ddl.indexDropped', { index: item.name }), color: 'success', icon: 'i-lucide-circle-check' })
    emit('changed', result)
  } finally {
    removing.value = null
  }
}

defineExpose({ addColumn: () => editColumn(null), editColumn, dropColumn, addIndex: () => (indexOpen.value = true), dropIndex, table, removing })
</script>

<template>
  <ExplorerColumnModal v-model:open="columnOpen" :source-id="sourceId" :engine="engine" :structure="structure" :column="column" @done="result => emit('changed', result)" />
  <ExplorerIndexModal v-model:open="indexOpen" :source-id="sourceId" :engine="engine" :structure="structure" @done="result => emit('changed', result)" />
  <ExplorerTableModal v-model:open="tableOpen" :source-id="sourceId" :engine="engine" :structure="structure" :mode="tableMode" @done="result => emit('changed', result)" />
</template>
