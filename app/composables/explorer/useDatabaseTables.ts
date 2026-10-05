/**
 * A connection's tables for the explorer tree and the Query editor (F12, lazy for very large
 * databases): the names come first (up to TREE_PAGE_SIZE, searched on the server when there are
 * more), a table's columns load only when it is opened, or named in the editor, and stay cached
 * for the connection.
 */
import type { DatabaseTable, TableColumn } from '#shared/types/destinations'

/** Tables listed at once; beyond this the tree asks the server for the ones searched for. */
const TREE_PAGE_SIZE = 500

export function useDatabaseTables(sourceId: Ref<string | null>) {
  const api = useApi()
  const { handle } = useErrorHandler()
  const tables = ref<DatabaseTable[] | null>(null)
  const error = ref<ApiError | null>(null)
  const loading = ref(false)
  /** More tables than were listed: search goes to the server. */
  const truncated = ref(false)
  const total = ref(0)
  const columns = reactive(new Map<string, TableColumn[]>())
  const pending = new Map<string, Promise<TableColumn[] | null>>()
  const keyOf = (table: Pick<DatabaseTable, 'schema' | 'name'>) => `${table.schema}.${table.name}`
  let query = ''
  let request = 0

  async function load(keep = false, q = query) {
    if (!sourceId.value) return
    query = q
    const mine = ++request
    loading.value = true
    error.value = null
    if (!keep) tables.value = null
    try {
      const { data, meta } = await api.list<DatabaseTable>(`/datasources/${sourceId.value}/explorer/tables`, { columns: 'none', page_size: TREE_PAGE_SIZE, ...(q ? { q } : {}) })
      if (mine !== request) return
      tables.value = data
      total.value = meta.total
      if (!q) truncated.value = meta.total > data.length
    } catch (problem) {
      if (mine === request) error.value = handle(problem, { silent: true })
    } finally {
      if (mine === request) loading.value = false
    }
  }

  /** Search: in the browser when every table is listed, otherwise on the server (debounced). */
  const searchServer = useDebounceFn((q: string) => void load(true, q), 300)
  const search = (q: string) => truncated.value && searchServer(q.trim())

  /** A table's columns (loaded once per table and connection). */
  function loadColumns(table: Pick<DatabaseTable, 'schema' | 'name'>) {
    const key = keyOf(table)
    if (columns.has(key)) return Promise.resolve(columns.get(key)!)
    if (!pending.has(key)) {
      const id = sourceId.value
      pending.set(
        key,
        api
          .get<TableColumn[]>(`/datasources/${id}/explorer/columns`, { schema: table.schema, table: table.name }, { background: true })
          .then(({ data }) => {
            if (id === sourceId.value) columns.set(key, data)
            return data
          })
          .catch(() => null)
          .finally(() => pending.delete(key)),
      )
    }
    return pending.get(key)!
  }
  const reset = () => {
    columns.clear()
    pending.clear()
    query = ''
    truncated.value = false
  }
  /** After a structure change: drop that table's columns (or all) and list again. */
  async function refresh(table?: Pick<DatabaseTable, 'schema' | 'name'>) {
    if (table) columns.delete(keyOf(table))
    else columns.clear()
    await load(true)
  }

  watch(sourceId, () => {
    reset()
    void load()
  }, { immediate: true })

  return { tables, error, loading, truncated, total, columns, keyOf, load, search, loadColumns, refresh }
}
