/**
 * Data sources (F12) helpers for the UI: status colours (theme colours only: green · amber · red ·
 * ink · violet), engine names and logos, and the connection test runner (start, then follow the
 * steps until it finishes; Cancel stops following).
 */
import type { BadgeProps } from '@nuxt/ui'
import type { ConnectionTest, ConnectionTestRequest, DataSourceStatus } from '#shared/types/datasources'
import { databaseOf } from '#shared/utils/integrations/databases'

export const DATASOURCE_STATUS_META: Record<DataSourceStatus, { color: BadgeProps['color']; fill: string; icon: string }> = {
  connected: { color: 'success', fill: 'bg-green-500', icon: 'i-lucide-circle-check' },
  attention: { color: 'warning', fill: 'bg-amber-500', icon: 'i-lucide-triangle-alert' },
  failing: { color: 'error', fill: 'bg-red-500', icon: 'i-lucide-circle-x' },
  disabled: { color: 'neutral', fill: 'bg-(--ui-text-dimmed)', icon: 'i-lucide-circle-pause' },
  untested: { color: 'secondary', fill: 'bg-violet-600', icon: 'i-lucide-circle-help' },
}

export const engineName = (engine: string) => databaseOf(engine)?.name ?? engine
export const engineIcon = (engine: string) => databaseOf(engine)?.icon ?? 'i-lucide-database'

const POLL_MS = 400

export function useConnectionTest() {
  const api = useApi()
  const { handle } = useErrorHandler()
  const test = ref<ConnectionTest | null>(null)
  const running = computed(() => !!test.value && test.value.status === 'running')
  const starting = ref(false)
  let token = 0

  async function follow(id: string, mine: number) {
    while (mine === token) {
      const { data } = await api.get<ConnectionTest>(`/datasources/tests/${id}`, undefined, { background: true })
      if (mine !== token) return
      test.value = data
      if (data.status !== 'running') return
      await new Promise(resolve => setTimeout(resolve, POLL_MS))
    }
  }

  /** Test a configuration (new, or a saved connection with changes), or a saved one as it is. */
  async function start(input: ConnectionTestRequest | { savedId: string }): Promise<ConnectionTest | null> {
    const mine = ++token
    starting.value = true
    test.value = null
    try {
      const { data } = 'savedId' in input ? await api.post<{ id: string }>(`/datasources/${input.savedId}/test`) : await api.post<{ id: string }>('/datasources/test', input)
      await follow(data.id, mine)
      return mine === token ? test.value : null
    } catch (error) {
      if (mine === token) handle(error)
      return null
    } finally {
      if (mine === token) starting.value = false
    }
  }

  function reset() {
    token++
    test.value = null
    starting.value = false
  }
  onScopeDispose(() => token++)

  return { test, running, starting, start, reset }
}
