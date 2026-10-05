/**
 * Running statements in the Query editor (F12 M4): one at a time per tab, cancellable, with the
 * confirm step for anything that changes rows or structure (the server says what it will do), and
 * problems turned into something to show: the database's own message and the line it points at.
 * Results live in memory only (never stored in the browser).
 */
import type { QueryHistoryItem, QueryResult } from '#shared/types/query'
import type { StatementKind } from '#shared/utils/datasources/sql'

export interface QueryProblem {
  title: string
  description: string
  /** Line in the tab's text, when the database pointed at one. */
  line: number | null
}
export interface RunState {
  running: boolean
  result: QueryResult | null
  problem: QueryProblem | null
  /** What ran last, to page through it again. */
  last: { text: string; from: number; params: Record<string, string>; confirmed: boolean } | null
}

export function useQueryRunner(sourceId: Ref<string | null>, lineAt: (position: number) => number) {
  const { t } = useI18n()
  const api = useApi()
  const { handle, messageFor } = useErrorHandler()
  const confirm = useConfirm()
  const { number } = useFormat()
  const states = reactive(new Map<string, RunState>())
  const controllers = new Map<string, AbortController>()
  const history = ref<QueryHistoryItem[] | null>(null)

  const stateOf = (tabId: string): RunState => {
    if (!states.has(tabId)) states.set(tabId, { running: false, result: null, problem: null, last: null })
    return states.get(tabId)!
  }

  async function loadHistory() {
    if (!sourceId.value) return
    try {
      history.value = (await api.get<QueryHistoryItem[]>(`/datasources/${sourceId.value}/query-history`, undefined, { background: true })).data
    } catch {
      history.value = []
    }
  }
  async function removeHistory(id?: string) {
    if (!sourceId.value) return
    try {
      await api.del(`/datasources/${sourceId.value}/query-history`, { query: id ? { id } : {} })
      history.value = id ? (history.value ?? []).filter(item => item.id !== id) : []
    } catch (error) {
      handle(error)
    }
  }

  async function run(tabId: string, text: string, from: number, params: Record<string, string>, page = 1, confirmed = false) {
    if (!sourceId.value) return
    const state = stateOf(tabId)
    controllers.get(tabId)?.abort()
    const controller = new AbortController()
    controllers.set(tabId, controller)
    state.running = true
    state.problem = null
    try {
      const { data } = await api.post<QueryResult>(`/datasources/${sourceId.value}/query`, { sql: text, params, page, page_size: 50, confirm: confirmed }, { signal: controller.signal })
      state.result = data
      state.last = { text, from, params, confirmed }
    } catch (error) {
      if (controller.signal.aborted) return
      const normalised = handle(error, { silent: true })
      const detail = (field: string) => normalised.details?.find(item => item.field === field)?.message ?? ''
      if (normalised.code === 'FRM-DEST-1023') {
        // A changing statement: say what it will do, then run it on a yes.
        const kind = detail('kind') as StatementKind
        const estimate = detail('estimate')
        const tables = detail('tables').split(',').filter(Boolean).join(', ')
        state.running = false
        const yes = await confirm({
          title: t(`query.confirm.${kind}`, { tables: tables || t('query.confirm.theTable') }),
          description: [estimate ? t('query.confirm.rows', { n: number(Number(estimate)) }, Number(estimate)) : '', t('query.confirm.cantUndo')].filter(Boolean).join(' '),
          confirmLabel: t('query.confirm.run'),
          danger: kind === 'delete' || kind === 'structure',
        })
        if (yes) await run(tabId, text, from, params, page, true)
        return
      }
      const message = detail('message')
      const position = Number(detail('position') || 0)
      state.problem = {
        title: normalised.code === 'FRM-DEST-1025' ? t('query.problemTitle') : messageFor(normalised),
        description:
          normalised.code === 'FRM-DEST-1025'
            ? message === 'preview_unsupported'
              ? t('query.previewUnsupported')
              : message
            : normalised.code === 'FRM-DEST-1019' && detail('table') === 'response_table'
              ? t('explorer.readOnly.response_table')
              : '',
        line: normalised.code === 'FRM-DEST-1025' ? lineAt(from + position) : null,
      }
      state.result = null
    } finally {
      if (controllers.get(tabId) === controller) {
        controllers.delete(tabId)
        state.running = false
        void loadHistory()
      }
    }
  }

  function cancel(tabId: string) {
    controllers.get(tabId)?.abort()
    controllers.delete(tabId)
    const state = stateOf(tabId)
    state.running = false
    state.problem = { title: t('query.cancelled'), description: '', line: null }
  }

  const page = (tabId: string, to: number) => {
    const last = stateOf(tabId).last
    if (last) void run(tabId, last.text, last.from, last.params, to, last.confirmed)
  }

  return { stateOf, run, cancel, page, history, loadHistory, removeHistory }
}
