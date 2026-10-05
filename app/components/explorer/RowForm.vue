<!--
  Add or change a row (F12 M3; Full access, the organisation's own tables only). One field per
  column, the right control for its type (number, yes / no, date, date and time, JSON, text);
  empty means NULL where the column allows it. The key is set automatically on a new row when the
  table numbers it, and never changes on an existing row. Checked here and again on the server;
  problems show under their column.
-->
<script setup lang="ts">
import type { ExplorerColumn, TableRow, TableStructure } from '#shared/types/explorer'
import { kindOfType, lengthOf, parseValue } from '#shared/utils/datasources/values'

const props = defineProps<{ sourceId: string; structure: TableStructure; row: TableRow | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [row: TableRow] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()

const values = ref<Record<string, string | boolean | null>>({})
const errors = ref<Record<string, string>>({})
const saving = ref(false)
const editing = computed(() => !!props.row)
const asText = (value: unknown) =>
  value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value)
watch(open, isOpen => {
  if (!isOpen) return
  errors.value = {}
  values.value = Object.fromEntries(
    props.structure.columns.map(column => {
      const value = props.row?.[column.name]
      if (kindOfType(column.type) === 'boolean')
        return [
          column.name,
          value == null ? (props.row ? null : false) : value === true || value === 1 || value === 'true',
        ]
      if (kindOfType(column.type) === 'datetime' && value) return [column.name, String(value).slice(0, 16)]
      return [column.name, props.row ? asText(value) : '']
    }),
  )
})
const locked = (column: ExplorerColumn) => column.primary && (editing.value || column.has_default)
const inputType = (column: ExplorerColumn) =>
  ({ integer: 'number', decimal: 'number', date: 'date', datetime: 'datetime-local', time: 'time' })[
    kindOfType(column.type) as 'integer'
  ] ?? 'text'
const problem = (code: string) => t(`explorer.problem.${code}`, { max: 0 })

async function save() {
  errors.value = {}
  const body: Record<string, unknown> = {}
  for (const column of props.structure.columns) {
    if (locked(column)) continue
    const raw = values.value[column.name]
    const parsed = parseValue(column, raw)
    if ('problem' in parsed)
      errors.value[column.name] =
        parsed.problem === 'length'
          ? t('explorer.problem.length', { max: lengthOf(column.type) ?? 0 })
          : problem(parsed.problem)
    else body[column.name] = raw
  }
  if (Object.keys(errors.value).length) return
  saving.value = true
  try {
    const query = { schema: props.structure.schema, table: props.structure.name }
    const { data } = props.row
      ? await api.patch<TableRow>(`/datasources/${props.sourceId}/explorer/rows`, {
          ...query,
          key: props.row.__key,
          values: body,
        })
      : await api.post<TableRow>(`/datasources/${props.sourceId}/explorer/rows`, { ...query, values: body })
    useToast().add({
      title: props.row ? t('explorer.rowSaved') : t('explorer.rowAdded'),
      color: 'success',
      icon: 'i-lucide-circle-check',
    })
    emit('saved', data)
    open.value = false
  } catch (error) {
    const normalised = handle(error, { silent: true })
    if (normalised.details?.length)
      for (const detail of normalised.details) errors.value[detail.field] = problem(detail.message)
    else handle(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppModal
    v-model:open="open"
    keep-open
    :title="row ? t('explorer.editRow', { key: row.__key }) : t('explorer.addRow')"
    :description="`${structure.schema}.${structure.name}`"
    :dismissible="!saving"
    :ui="{ content: 'sm:max-w-2xl' }"
  >
    <template #body>
      <form id="row-form" class="grid grid-cols-1 gap-4 sm:grid-cols-2" novalidate @submit.prevent="save">
        <UFormField
          v-for="column in structure.columns"
          :key="column.name"
          :name="column.name"
          :error="errors[column.name]"
          :required="!column.nullable && !column.has_default"
          :class="
            kindOfType(column.type) === 'json' || /TEXT|CLOB|MAX/i.test(column.type) ? 'sm:col-span-2' : ''
          "
        >
          <template #label>
            <span class="font-mono text-xs" dir="ltr">{{ column.name }}</span>
          </template>
          <UInput
            v-if="locked(column)"
            :model-value="editing ? String(values[column.name] ?? '') : t('explorer.setAutomatically')"
            disabled
            class="w-full font-mono"
          />
          <USwitch
            v-else-if="kindOfType(column.type) === 'boolean'"
            :model-value="!!values[column.name]"
            :label="values[column.name] ? t('dataSources.yes') : t('dataSources.no')"
            @update:model-value="value => (values[column.name] = !!value)"
          />
          <UTextarea
            v-else-if="kindOfType(column.type) === 'json' || /TEXT|CLOB|MAX/i.test(column.type)"
            v-model="values[column.name] as string"
            :rows="3"
            autoresize
            :maxrows="10"
            class="w-full"
            :ui="{ base: kindOfType(column.type) === 'json' ? 'font-mono text-xs' : '' }"
            :placeholder="column.nullable ? t('explorer.emptyIsNull') : undefined"
            dir="auto"
          />
          <UInput
            v-else
            v-model="values[column.name] as string"
            :type="inputType(column)"
            :step="kindOfType(column.type) === 'decimal' ? 'any' : undefined"
            class="w-full"
            :placeholder="column.nullable ? t('explorer.emptyIsNull') : undefined"
            :maxlength="lengthOf(column.type) ?? undefined"
            dir="auto"
          />
        </UFormField>
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton
          :label="t('common.cancel')"
          color="neutral"
          variant="outline"
          :disabled="saving"
          @click="open = false"
        />
        <UButton
          type="submit"
          form="row-form"
          :label="row ? t('common.save') : t('explorer.addRow')"
          icon="i-lucide-check"
          color="neutral"
          :loading="saving"
        />
      </div>
    </template>
  </AppModal>
</template>
