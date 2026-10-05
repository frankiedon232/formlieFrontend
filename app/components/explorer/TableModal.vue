<!--
  Rename, empty (TRUNCATE) or delete (DROP) the organisation's own table (F12 M3). Emptying and
  deleting can't be undone: the person types the table's name to confirm, and sees the exact
  statement first.
-->
<script setup lang="ts">
import type { SchemaResult, TableStructure } from '#shared/types/explorer'
import { changeStatements, checkName, normaliseName, type TableChange } from '#shared/utils/datasources/ddl'
import type { DbEngine } from '#shared/utils/integrations/databases'

const props = defineProps<{ sourceId: string; engine: DbEngine; structure: TableStructure; mode: 'rename' | 'truncate' | 'drop' }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ done: [result: SchemaResult] }>()
const { t } = useI18n()
const { number } = useFormat()
const { busy, errors, change } = useSchemaChange()

const name = ref('')
const typed = ref('')
watch(open, isOpen => {
  if (!isOpen) return
  name.value = props.structure.name
  typed.value = ''
  errors.value = {}
})
const step = computed<TableChange>(() => (props.mode === 'rename' ? { op: 'rename_table', name: name.value } : props.mode === 'truncate' ? { op: 'truncate' } : { op: 'drop_table' }))
const statements = computed(() => (props.mode === 'rename' && (!name.value || name.value === props.structure.name) ? [] : changeStatements(props.engine, props.structure.schema, props.structure.name, step.value)))
const danger = computed(() => props.mode !== 'rename')
const confirmed = computed(() => !danger.value || typed.value.trim() === props.structure.name)

async function submit() {
  if (props.mode === 'rename') {
    name.value = normaliseName(props.engine, name.value)
    if (name.value === props.structure.name) return void (open.value = false)
    const problem = checkName(props.engine, name.value, 'table')
    if (problem) return void (errors.value = { name: t(`explorer.ddl.problem.${problem}`) })
  }
  if (!confirmed.value) return
  const result = await change(props.sourceId, props.structure.schema, props.structure.name, step.value)
  if (!result) return
  useToast().add({ title: t(`explorer.ddl.done.${props.mode}`, { table: result.table?.name ?? props.structure.name }), color: 'success', icon: 'i-lucide-circle-check' })
  open.value = false
  emit('done', result)
}
</script>

<template>
  <AppModal keep-open v-model:open="open" :title="t(`explorer.ddl.${mode}Title`, { table: structure.name })" :description="`${structure.schema}.${structure.name}`" :dismissible="!busy" :ui="{ content: 'sm:max-w-lg' }">
    <template #body>
      <form id="table-form" class="flex flex-col gap-4" novalidate @submit.prevent="submit">
        <UFormField v-if="mode === 'rename'" :label="t('explorer.ddl.tableName')" :error="errors.name" required>
          <UInput v-model="name" autofocus class="w-full font-mono" dir="ltr" @blur="name = normaliseName(engine, name)" />
        </UFormField>
        <template v-else>
          <UAlert
            icon="i-lucide-triangle-alert"
            color="error"
            variant="subtle"
            :title="t(`explorer.ddl.${mode}Warning`, { n: number(structure.rows_estimate ?? 0) }, structure.rows_estimate ?? 0)"
            :description="t('explorer.ddl.cantUndo')"
          />
          <UFormField :label="t('explorer.ddl.typeToConfirm', { table: structure.name })">
            <UInput v-model="typed" autofocus class="w-full font-mono" dir="ltr" autocomplete="off" :placeholder="structure.name" />
          </UFormField>
        </template>
        <p v-if="mode === 'rename'" class="flex gap-1.5 text-xs text-muted"><UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" /> {{ t('explorer.ddl.renameNote') }}</p>
        <ExplorerSqlPreview :statements="statements" />
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" :disabled="busy" @click="open = false" />
        <UButton
          type="submit"
          form="table-form"
          :label="t(`explorer.ddl.${mode}Button`)"
          :icon="mode === 'rename' ? 'i-lucide-check' : mode === 'truncate' ? 'i-lucide-eraser' : 'i-lucide-trash-2'"
          :color="danger ? 'error' : 'neutral'"
          :disabled="!confirmed"
          :loading="busy"
        />
      </div>
    </template>
  </AppModal>
</template>
