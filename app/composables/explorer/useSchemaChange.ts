/**
 * Sends a structure change (or a new table) for the explorer's dialogs (F12 M3): busy state,
 * problems mapped to the dialog's fields (`explorer.ddl.problem.*`), other errors as a toast.
 * Resolves with the server's answer, or null when it didn't go through.
 */
import type { SchemaResult } from '#shared/types/explorer'
import type { ColumnSpec, TableChange } from '#shared/utils/datasources/ddl'

export function useSchemaChange() {
  const api = useApi()
  const { t } = useI18n()
  const { handle } = useErrorHandler()
  const busy = ref(false)
  const errors = ref<Record<string, string>>({})

  async function send(path: string, body: Record<string, unknown>): Promise<SchemaResult | null> {
    errors.value = {}
    busy.value = true
    try {
      return (await api.post<SchemaResult>(path, body)).data
    } catch (error) {
      const normalised = handle(error, { silent: true })
      if (normalised.details?.length) for (const detail of normalised.details) errors.value[detail.field] = t(`explorer.ddl.problem.${detail.message}`)
      else handle(error)
      return null
    } finally {
      busy.value = false
    }
  }

  return {
    busy,
    errors,
    change: (sourceId: string, schema: string, table: string, change: TableChange) => send(`/datasources/${sourceId}/explorer/changes`, { schema, table, change }),
    create: (sourceId: string, schema: string, name: string, columns: ColumnSpec[]) => send(`/datasources/${sourceId}/explorer/tables`, { schema, name, columns }),
  }
}
