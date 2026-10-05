/**
 * State for setting up (or changing) where a form's responses are stored (F12 M2): the
 * connection, a new table from the form or a table of theirs, the columns, the options. Columns of
 * a new table follow the form and the options (renames are kept); an existing table's columns are
 * matched to the form once, then edited by hand. Checks run on every change.
 */
import type { DataSourceDetail, DataSourceRow } from '#shared/types/datasources'
import type { DatabaseTable, DestinationColumn, DestinationDetail, DestinationSettings, MetaColumn, StorageField } from '#shared/types/destinations'
import { tablesSchemaOf } from '#shared/utils/datasources/permissions'
import { checkMapping, columnsForForm, matchColumns, metaTypeFor, tableNameFor } from '#shared/utils/datasources/tables'

export function useStorageSetup(input: { formName: () => string; fields: () => StorageField[]; destination?: DestinationDetail | null }) {
  const api = useApi()
  const { handle } = useErrorHandler()

  const sources = ref<DataSourceRow[] | null>(null)
  const sourceId = ref<string | null>(input.destination?.datasource.id ?? null)
  const source = ref<DataSourceDetail | null>(null)
  const tables = ref<DatabaseTable[] | null>(null)
  const loadingTables = ref(false)

  const mode = ref<'create' | 'existing'>(input.destination ? (input.destination.table.created ? 'create' : 'existing') : 'create')
  const tableName = ref(input.destination?.table.name ?? '')
  const existingKey = ref<string | null>(input.destination && !input.destination.table.created ? `${input.destination.table.schema}.${input.destination.table.name}` : null)
  const settings = ref<DestinationSettings>(input.destination ? { ...input.destination.settings } : { write_mode: 'insert', key_column: 'response_id', multi_value: 'json', choices: 'value' })
  const extraMeta = ref<MetaColumn[]>([])
  const renames = ref<Record<string, string>>({})
  const skipped = ref<string[]>([])
  const manual = ref<DestinationColumn[] | null>(input.destination ? input.destination.columns.map(column => ({ ...column })) : null)

  async function loadSources() {
    try {
      sources.value = (await api.list<DataSourceRow>('/datasources', { page_size: 100, sort: 'name' })).data.filter(item => item.enabled)
    } catch (error) {
      sources.value = []
      handle(error)
    }
  }
  async function loadSource(id: string) {
    loadingTables.value = true
    try {
      const [detail, list] = await Promise.all([api.get<DataSourceDetail>(`/datasources/${id}`), api.get<DatabaseTable[]>(`/datasources/${id}/tables`)])
      source.value = detail.data
      tables.value = list.data
      if (!input.destination && !tableName.value) tableName.value = suggestedName()
    } catch (error) {
      handle(error)
    } finally {
      loadingTables.value = false
    }
  }
  watch(sourceId, (id, old) => {
    if (!id) return
    if (old && !input.destination) {
      tableName.value = ''
      existingKey.value = null
      manual.value = null
    }
    void loadSource(id)
  }, { immediate: true })

  const engine = computed(() => source.value?.engine ?? null)
  const fullAccess = computed(() => source.value?.access.other === 'read_write')
  const tablesSchema = computed(() => (source.value ? tablesSchemaOf(source.value.engine, source.value.settings, source.value.access) : ''))
  const suggestedName = () => (source.value ? tableNameFor(source.value.engine, source.value.access.table_prefix, input.formName()) : '')
  const prefix = computed(() => (source.value ? (source.value.engine === 'oracle' ? source.value.access.table_prefix.toUpperCase() : source.value.access.table_prefix) : ''))
  const theirTables = computed(() => (tables.value ?? []).filter(table => !table.formalie))
  const existing = computed(() => theirTables.value.find(table => `${table.schema}.${table.name}` === existingKey.value) ?? null)
  const nameTaken = computed(() => (tables.value ?? []).some(table => table.schema === tablesSchema.value && table.name.toLowerCase() === tableName.value.trim().toLowerCase()))

  // A table of theirs: matched once when picked, then edited by hand.
  watch(existing, table => {
    if (!table || input.destination) return
    manual.value = matchColumns(table.columns, input.fields() as never[])
  })
  watch(mode, value => value === 'create' && !input.destination && (manual.value = null))

  /** The columns as they would be written. */
  const columns = computed<DestinationColumn[]>(() => {
    if (mode.value === 'existing' || input.destination) return manual.value ?? []
    if (!engine.value) return []
    const fields = input.fields().filter(field => !skipped.value.includes(field.key))
    const meta: MetaColumn[] = ['response_id', 'submitted_at', 'form_version', 'language', ...extraMeta.value]
    return columnsForForm(engine.value, fields as never[], settings.value, meta).map(column => {
      const key = column.source ? `${column.source.kind}:${column.source.key}` : ''
      return renames.value[key] ? { ...column, column: renames.value[key]! } : column
    })
  })
  const issues = computed(() => checkMapping(columns.value, input.fields() as never[], settings.value))

  /** A table of theirs without a place for the response id: add a column for it (Full access). */
  function addKeyColumn() {
    if (!engine.value || !manual.value) return
    const name = engine.value === 'oracle' ? 'FORMALIE_RESPONSE_ID' : 'formalie_response_id'
    manual.value = [...manual.value, { column: name, type: metaTypeFor(engine.value, 'response_id'), source: { kind: 'meta', key: 'response_id' }, nullable: true, existing: false }]
  }

  return { sources, sourceId, source, tables, loadingTables, mode, tableName, existingKey, settings, extraMeta, renames, skipped, manual, engine, fullAccess, tablesSchema, prefix, theirTables, existing, nameTaken, columns, issues, loadSources, suggestedName, addKeyColumn }
}

