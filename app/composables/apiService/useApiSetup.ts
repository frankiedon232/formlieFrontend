/**
 * How far the organisation's API service is set up (guided setup, F13 M7): services, endpoints,
 * live endpoints, tokens and access rules. One copy shared by the overview, the dialogs and the
 * panels; anything that creates or changes one of these calls `refresh()`.
 */
import type { ApiSetupSummary } from '#shared/types/apiService'

const summary = ref<ApiSetupSummary | null>(null)
let loading: Promise<void> | null = null

export function useApiSetup() {
  const api = useApi()
  async function refresh() {
    loading ??= (async () => {
      try {
        summary.value = (await api.get<ApiSetupSummary>('/api-service/setup', undefined, { background: true })).data
      } catch {
        // The guide simply shows every step as open
      } finally {
        loading = null
      }
    })()
    return loading
  }
  if (!summary.value) void refresh()
  return { summary: readonly(summary), refresh }
}
