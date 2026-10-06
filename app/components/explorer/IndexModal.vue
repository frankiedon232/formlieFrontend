<!-- Add an index to the organisation's own table (F12 M3): its columns in order, unique or not, the exact CREATE INDEX first. -->
<script setup lang="ts">
import type { SchemaResult, TableStructure } from '#shared/types/explorer'
import { changeStatements, checkName, normaliseDbName } from '#shared/utils/datasources/ddl'
import type { DbEngine } from '#shared/utils/integrations/databases'

const props = defineProps<{ sourceId: string; engine: DbEngine; structure: TableStructure }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ done: [result: SchemaResult] }>()
const { t } = useI18n()
const { busy, errors, change } = useSchemaChange()

const name = ref('')
const columns = ref<string[]>([])
const unique = ref(false)
const named = ref(false)
watch(open, isOpen => {
  if (!isOpen) return
  columns.value = []
  unique.value = false
  named.value = false
  name.value = ''
  errors.value = {}
})
// The name follows the columns until someone types one.
watch([columns, unique], () => {
  if (named.value) return
  name.value = columns.value.length ? normaliseDbName(props.engine, `${props.structure.name}_${columns.value.join('_')}_${unique.value ? 'uq' : 'idx'}`).slice(0, 60) : ''
})
const items = computed(() => props.structure.columns.map(column => column.name))
const statements = computed(() => (name.value && columns.value.length ? changeStatements(props.engine, props.structure.schema, props.structure.name, { op: 'add_index', name: name.value, columns: columns.value, unique: unique.value }) : []))

async function submit() {
  const local: Record<string, string> = {}
  if (!columns.value.length) local.columns = t('explorer.ddl.problem.columns')
  const problem = checkName(props.engine, name.value, 'index')
  if (problem) local.name = t(`explorer.ddl.problem.${problem}`)
  errors.value = local
  if (Object.keys(local).length) return
  const result = await change(props.sourceId, props.structure.schema, props.structure.name, { op: 'add_index', name: name.value, columns: columns.value, unique: unique.value })
  if (!result) return
  useToast().add({ title: t('explorer.ddl.indexAdded', { index: name.value }), color: 'success', icon: 'i-lucide-circle-check' })
  open.value = false
  emit('done', result)
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="t('explorer.ddl.addIndex')" :description="`${structure.schema}.${structure.name}`" :dismissible="!busy" :ui="{ content: 'sm:max-w-xl' }">
    <template #body>
      <form id="index-form" class="flex flex-col gap-4" novalidate @submit.prevent="submit">
        <UFormField :label="t('explorer.ddl.indexColumns')" :error="errors.columns" :help="t('explorer.ddl.indexColumnsHelp')" required>
          <USelectMenu v-model="columns" :items="items" multiple class="w-full font-mono" :placeholder="t('explorer.ddl.pickColumns')" />
        </UFormField>
        <USwitch v-model="unique" :label="t('explorer.ddl.unique')" :description="t('explorer.ddl.uniqueDesc')" />
        <UFormField :label="t('explorer.ddl.indexName')" :error="errors.name" required>
          <UInput :model-value="name" class="w-full font-mono" dir="ltr" @update:model-value="value => ((name = String(value)), (named = true))" @blur="name = normaliseDbName(engine, name)" />
        </UFormField>
        <ExplorerSqlPreview :statements="statements" />
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" :disabled="busy" @click="open = false" />
        <UButton type="submit" form="index-form" :label="t('explorer.ddl.addIndex')" icon="i-lucide-check" color="neutral" :loading="busy" />
      </div>
    </template>
  </AppModal>
</template>
