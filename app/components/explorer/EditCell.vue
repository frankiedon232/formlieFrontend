<!--
  A table cell that edits in place, like a database editor (owner 2026-10-05): a double-click turns
  it into the control for its type; Enter or leaving the cell saves just that value, Esc cancels
  (keyboard: the row's Edit, in its panel or right-click menu, opens the row form). Checked here and on the server with the same rules as
  the row form; a problem shows on the cell. Never for keys, auto-numbered or UUID columns, or
  tables that are read only here (response tables, Read only access, views, no key). Long text
  and JSON open the row form instead.
-->
<script setup lang="ts">
import type { ExplorerColumn, TableRow, TableStructure } from '#shared/types/explorer'
import { kindOfType, lengthOf, parseValue } from '#shared/utils/datasources/values'

const props = defineProps<{ row: TableRow; column: ExplorerColumn; structure: TableStructure; sourceId: string }>()
const emit = defineEmits<{ start: []; long: []; saved: [values: TableRow] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const kind = computed(() => kindOfType(props.column.type))
const editable = computed(() => {
  const column = props.column
  if (props.structure.read_only || column.primary) return false
  if (/UUID|UNIQUEIDENTIFIER/i.test(column.type) || /(^|_)(uuid|guid)$/i.test(column.name)) return false
  const value = props.row[column.name]
  return !(typeof value === 'string' && UUID.test(value))
})
const long = computed(() => kind.value === 'json' || /TEXT|CLOB|MAX/i.test(props.column.type))

const editing = ref(false)
const draft = ref('')
const error = ref<string | null>(null)
const saving = ref(false)
const input = useTemplateRef<{ inputRef?: HTMLInputElement }>('input')
const asText = (value: unknown) => (value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value))

function start() {
  if (!editable.value || saving.value) return
  emit('start')
  if (long.value) return void emit('long')
  const value = props.row[props.column.name]
  draft.value = kind.value === 'boolean' ? (value == null ? '' : String(value === true || value === 1 || value === 'true')) : kind.value === 'datetime' && value ? asText(value).slice(0, 16) : asText(value)
  error.value = null
  editing.value = true
  void nextTick(() => {
    input.value?.inputRef?.focus()
    input.value?.inputRef?.select()
  })
}
function cancel() {
  editing.value = false
  error.value = null
}
async function save() {
  if (!editing.value || saving.value) return
  const raw = kind.value === 'boolean' ? (draft.value === '' ? null : draft.value === 'true') : draft.value
  const before = props.row[props.column.name]
  if ((raw ?? '') === (kind.value === 'boolean' ? (before ?? '') : asText(before))) return cancel()
  const parsed = parseValue(props.column, raw)
  if ('problem' in parsed) return void (error.value = t(`explorer.problem.${parsed.problem}`, { max: lengthOf(props.column.type) ?? 0 }))
  saving.value = true
  try {
    const { data } = await api.patch<TableRow>(`/datasources/${props.sourceId}/explorer/rows`, { schema: props.structure.schema, table: props.structure.name, key: props.row.__key, values: { [props.column.name]: raw } })
    emit('saved', data)
    editing.value = false
    useToast().add({ title: t('explorer.cellSaved', { column: props.column.name }), color: 'success', icon: 'i-lucide-circle-check' })
  } catch (caught) {
    const normalised = handle(caught, { silent: true })
    const detail = normalised.details?.find(item => item.field === props.column.name)
    if (detail) error.value = t(`explorer.problem.${detail.message}`, { max: lengthOf(props.column.type) ?? 0 })
    else handle(caught)
  } finally {
    saving.value = false
  }
}
function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    event.preventDefault()
    void save()
  } else if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    cancel()
  }
}
const inputType = computed(() => ({ integer: 'number', decimal: 'number', date: 'date', datetime: 'datetime-local', time: 'time' })[kind.value as 'integer'] ?? 'text')
const choices = computed(() => [{ value: 'true', label: t('dataSources.yes') }, { value: 'false', label: t('dataSources.no') }, ...(props.column.nullable ? [{ value: '', label: 'NULL' }] : [])])
defineExpose({ start, editable })
</script>

<template>
  <div v-if="!editing" class="min-w-0" :class="editable ? 'cursor-text' : ''" :title="editable ? t('explorer.cellEditHint') : undefined" @dblclick.stop="start">
    <ExplorerCell :value="row[column.name]" />
  </div>
  <UTooltip v-else :text="error ?? ''" :open="!!error" :content="{ side: 'bottom', align: 'start' }">
    <div class="-mx-2 min-w-0" @dblclick.stop @click.stop>
      <USelect
        v-if="kind === 'boolean'"
        v-model="draft"
        :items="choices"
        value-key="value"
        size="xs"
        default-open
        class="w-full"
        :color="error ? 'error' : 'neutral'"
        :highlight="!!error"
        :loading="saving"
        @update:model-value="() => void save()"
        @update:open="open => !open && !saving && cancel()"
      />
      <UInput
        v-else
        ref="input"
        v-model="draft"
        :type="inputType"
        :step="kind === 'decimal' ? 'any' : undefined"
        :maxlength="lengthOf(column.type) ?? undefined"
        size="xs"
        class="w-full"
        :ui="{ base: 'h-6 rounded-sm font-mono text-xs' }"
        :color="error ? 'error' : 'neutral'"
        highlight
        :loading="saving"
        :aria-label="t('explorer.cellEdit', { column: column.name })"
        dir="auto"
        @keydown="onKeydown"
        @blur="save"
      />
    </div>
  </UTooltip>
</template>
