/**
 * Running statements in the Query editor (F12 M4): one statement (the selection or the one at the
 * cursor), or Run all (every statement of the tab in order, stopping at the first problem, a
 * result per statement). Cancellable; anything that changes rows or structure asks first (the
 * server says what it will do); problems become something to show: the database's own message and
 * the line it points at. Results live in memory only (never stored in the browser).
 */
import type { QueryHistoryItem, QueryResult } from '#shared/types/query'
import type { StatementKind } from '#shared/utils/datasources/sql'

export interface QueryProblem {
  title: string
  description: string
  /** Line in the tab's text, when the database pointed at one. */
  line: number | null
}
/** One statement of Run all, and what came of it. */
export interface BatchItem {
  text: string
  from: number
  params: Record<string, string>
  status: 'waiting' | 'running' | 'done' | 'failed' | 'skipped'
  result: QueryResult | null
  problem: QueryProblem | null
}
export interface RunState {
  running: boolean
  result: QueryResult | null
  problem: QueryProblem | null
  /** What ran last, to page through it again. */
  last: { text: string; from: number; params: Record<string, string>; confirmed: boolean; savedId?: string } | null
  /** Run all: every statement with its result; `active` is the one shown. */
  batch: BatchItem[] | null
  active: number
}
type Outcome = { result: QueryResult; confirmed: boolean } | { problem: QueryProblem } | { stopped: true }

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
    if (!states.has(tabId)) states.set(tabId, { running: false, result: null, problem: null, last: null, batch: null, active: 0 })
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

  /** One statement on the server: its result, its problem, or stopped (cancelled / not confirmed). */
  async function execute(text: string, from: number, params: Record<string, string>, page: number, savedId: string | undefined, signal: AbortSignal, confirmed = false): Promise<Outcome> {
    for (;;) {
      try {
        const { data } = await api.post<QueryResult>(`/datasources/${sourceId.value}/query`, { sql: text, params, page, page_size: 50, confirm: confirmed, saved_id: page === 1 ? savedId : undefined }, { signal })
        return { result: data, confirmed }
      } catch (error) {
        if (signal.aborted) return { stopped: true }
        const normalised = handle(error, { silent: true })
        const detail = (field: string) => normalised.details?.find(item => item.field === field)?.message ?? ''
        if (normalised.code === 'FRM-DEST-1023' && !confirmed) {
          // A changing statement: say what it will do, then run it on a yes.
          const kind = detail('kind') as StatementKind
          const estimate = detail('estimate')
          const tables = detail('tables').split(',').filter(Boolean).join(', ')
          const yes = await confirm({
            title: t(`query.confirm.${kind}`, { tables: tables || t('query.confirm.theTable') }),
            description: [estimate ? t('query.confirm.rows', { n: number(Number(estimate)) }, Number(estimate)) : '', t('query.confirm.cantUndo')].filter(Boolean).join(' '),
            confirmLabel: t('query.confirm.run'),
            danger: kind === 'delete' || kind === 'structure',
          })
          if (!yes || signal.aborted) return { stopped: true }
          confirmed = true
          continue
        }
        const message = detail('message')
        const position = Number(detail('position') || 0)
        return {
          problem: {
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
          },
        }
      }
    }
  }

  function begin(tabId: string) {
    controllers.get(tabId)?.abort()
    const controller = new AbortController()
    controllers.set(tabId, controller)
    const state = stateOf(tabId)
    state.running = true
    state.problem = null
    return { state, controller }
  }
  function end(tabId: string, controller: AbortController) {
    if (controllers.get(tabId) !== controller) return
    controllers.delete(tabId)
    stateOf(tabId).running = false
    void loadHistory()
  }

  async function run(tabId: string, text: string, from: number, params: Record<string, string>, page = 1, confirmed = false, savedId?: string) {
    if (!sourceId.value) return
    const { state, controller } = begin(tabId)
    if (page === 1) state.batch = null
    try {
      const outcome = await execute(text, from, params, page, savedId, controller.signal, confirmed)
      if ('result' in outcome) {
        state.result = outcome.result
        state.last = { text, from, params, confirmed: outcome.confirmed, savedId }
      } else if ('problem' in outcome) {
        state.problem = outcome.problem
        state.result = null
      }
    } finally {
      end(tabId, controller)
    }
  }

  /** Every statement in order; stops at the first problem or a "no" to a confirm. */
  async function runAll(tabId: string, statements: { text: string; from: number; params: Record<string, string> }[]) {
    if (!sourceId.value || !statements.length) return
    const { state, controller } = begin(tabId)
    state.result = null
    state.batch = statements.map(item => ({ ...item, status: 'waiting', result: null, problem: null }))
    state.active = 0
    try {
      for (const [index, item] of state.batch.entries()) {
        item.status = 'running'
        state.active = index
        const outcome = await execute(item.text, item.from, item.params, 1, undefined, controller.signal)
        if ('result' in outcome) {
          item.result = outcome.result
          item.status = 'done'
          continue
        }
        if ('problem' in outcome) {
          item.problem = outcome.problem
          item.status = 'failed'
        } else item.status = 'skipped'
        for (const rest of state.batch.slice(index + 1)) rest.status = 'skipped'
        break
      }
    } finally {
      end(tabId, controller)
    }
  }

  function cancel(tabId: string) {
    controllers.get(tabId)?.abort()
    controllers.delete(tabId)
    const state = stateOf(tabId)
    state.running = false
    for (const item of state.batch ?? []) if (item.status === 'running' || item.status === 'waiting') item.status = 'skipped'
    if (!state.batch) state.problem = { title: t('query.cancelled'), description: '', line: null }
  }

  /** Another page of the shown result (a single run, or the chosen statement of Run all). */
  async function page(tabId: string, to: number) {
    const state = stateOf(tabId)
    const item = state.batch?.[state.active]
    if (!item) {
      const last = state.last
      if (last) void run(tabId, last.text, last.from, last.params, to, last.confirmed, last.savedId)
      return
    }
    const { controller } = begin(tabId)
    try {
      const outcome = await execute(item.text, item.from, item.params, to, undefined, controller.signal, true)
      if ('result' in outcome) item.result = outcome.result
    } finally {
      end(tabId, controller)
    }
  }

  return { stateOf, run, runAll, cancel, page, history, loadHistory, removeHistory }
}
