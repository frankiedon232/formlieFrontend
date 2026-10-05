/**
 * The Query editor's tabs (F12 M4): several statements open at once, per connection, kept on this
 * device so a reload doesn't lose them (only the SQL text, never results: those stay in memory).
 */
export interface QueryTab {
  id: string
  title: string
  sql: string
}
interface TabsState {
  tabs: QueryTab[]
  active: string
}

const newId = () => Math.random().toString(36).slice(2, 10)

export function useQueryTabs(sourceId: Ref<string | null>) {
  const { t } = useI18n()
  const store = useLocalStorage<Record<string, TabsState>>('formalie:query-tabs', {})

  const nextTitle = (tabs: QueryTab[]) => {
    let n = tabs.length + 1
    while (tabs.some(tab => tab.title === t('query.tabTitle', { n }))) n++
    return t('query.tabTitle', { n })
  }
  const state = computed<TabsState>(() => {
    const id = sourceId.value ?? '_'
    const current = store.value[id]
    if (current?.tabs.length) return current
    const first: QueryTab = { id: newId(), title: t('query.tabTitle', { n: 1 }), sql: '' }
    return { tabs: [first], active: first.id }
  })
  const save = (next: TabsState) => (store.value = { ...store.value, [sourceId.value ?? '_']: next })

  const tabs = computed(() => state.value.tabs)
  const active = computed(() => tabs.value.find(tab => tab.id === state.value.active) ?? tabs.value[0]!)

  function add(sql = '', title?: string) {
    const tab: QueryTab = { id: newId(), title: title ?? nextTitle(tabs.value), sql }
    save({ tabs: [...tabs.value, tab], active: tab.id })
    return tab
  }
  function close(id: string) {
    const left = tabs.value.filter(tab => tab.id !== id)
    if (!left.length) return save({ tabs: [{ id: newId(), title: t('query.tabTitle', { n: 1 }), sql: '' }], active: '' })
    const index = tabs.value.findIndex(tab => tab.id === id)
    save({ tabs: left, active: state.value.active === id ? left[Math.max(0, index - 1)]!.id : state.value.active })
  }
  const select = (id: string) => save({ ...state.value, active: id })
  const update = (id: string, sql: string) => save({ ...state.value, tabs: tabs.value.map(tab => (tab.id === id ? { ...tab, sql } : tab)) })
  const rename = (id: string, title: string) => save({ ...state.value, tabs: tabs.value.map(tab => (tab.id === id ? { ...tab, title } : tab)) })

  return { tabs, active, add, close, select, update, rename }
}
