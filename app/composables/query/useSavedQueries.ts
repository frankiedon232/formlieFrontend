/**
 * Saved queries for the Query editor's side panel and dialogs (F12 M4 part 2): the connection's
 * saved statements (yours and shared ones), and saving, changing, sharing and deleting yours.
 */
import type { SavedQuery } from '#shared/types/query'

export function useSavedQueries(sourceId: Ref<string | null>) {
  const api = useApi()
  const { t } = useI18n()
  const toast = useToast()
  const confirm = useConfirm()
  const { handle } = useErrorHandler()
  const list = ref<SavedQuery[] | null>(null)
  /** The saved query whose action is running (its row shows busy). */
  const busy = ref<string | null>(null)

  async function load() {
    if (!sourceId.value) return
    try {
      list.value = (await api.list<SavedQuery>('/saved-queries', { 'filter[datasource]': sourceId.value, page_size: 100, sort: 'name' }, { background: true })).data
    } catch {
      list.value = []
    }
  }
  const get = async (id: string) => (await api.get<SavedQuery>(`/saved-queries/${id}`)).data

  async function create(values: { name: string; description: string | null; sql: string; shared: boolean }) {
    const { data } = await api.post<SavedQuery>('/saved-queries', { ...values, datasource_id: sourceId.value })
    void load()
    return data
  }
  async function update(id: string, values: Partial<Pick<SavedQuery, 'name' | 'description' | 'sql' | 'shared'>>) {
    const { data } = await api.patch<SavedQuery>(`/saved-queries/${id}`, values)
    void load()
    return data
  }
  async function toggleShare(item: SavedQuery) {
    busy.value = item.id
    try {
      await update(item.id, { shared: !item.shared })
      toast.add({ title: item.shared ? t('query.saved.unshared', { name: item.name }) : t('query.saved.sharedToast', { name: item.name }), color: 'success', icon: 'i-lucide-circle-check' })
    } catch (error) {
      handle(error)
    } finally {
      busy.value = null
    }
  }
  async function remove(item: SavedQuery): Promise<boolean> {
    if (!(await confirm({ title: t('query.saved.deleteTitle', { name: item.name }), description: t('query.saved.deleteDesc'), confirmLabel: t('query.saved.delete'), danger: true }))) return false
    busy.value = item.id
    try {
      await api.del(`/saved-queries/${item.id}`)
      toast.add({ title: t('query.saved.deleted', { name: item.name }), color: 'success', icon: 'i-lucide-circle-check' })
      void load()
      return true
    } catch (error) {
      handle(error)
      return false
    } finally {
      busy.value = null
    }
  }

  return { list, busy, load, get, create, update, toggleShare, remove }
}
