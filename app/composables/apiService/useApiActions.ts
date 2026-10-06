/**
 * Actions on API services and endpoints (F13), shared by the lists, cards and panels: switch on /
 * off, duplicate, delete (confirmed), copy an endpoint's address. `busy` is the id being worked on
 * (its row or card shows a spinner); `changed` runs after every change so lists and charts refresh.
 */
import type { ApiEndpoint, ApiService, ApiStatus, ApiToken } from '#shared/types/apiService'

export function useApiActions(changed: () => unknown) {
  const { t } = useI18n()
  const api = useApi()
  const confirm = useConfirm()
  const toast = useToast()
  const { handle } = useErrorHandler()
  const { copy } = useClipboard({ legacy: true })
  const busy = ref<string | null>(null)

  async function act<T>(id: string, work: () => Promise<T>, success: string): Promise<T | undefined> {
    if (busy.value) return undefined
    busy.value = id
    try {
      const result = await work()
      toast.add({ title: success, color: 'success', icon: 'i-lucide-circle-check' })
      await changed()
      return result
    } catch (error) {
      handle(error)
      return undefined
    } finally {
      busy.value = null
    }
  }

  const setServiceStatus = (service: Pick<ApiService, 'id' | 'name'>, status: ApiStatus) =>
    act(service.id, () => api.patch(`/api-services/${service.id}`, { status }), t(status === 'active' ? 'apiService.toast.serviceOn' : 'apiService.toast.serviceOff', { name: service.name }))
  const duplicateService = (service: Pick<ApiService, 'id' | 'name'>) =>
    act(service.id, async () => (await api.post<ApiService>(`/api-services/${service.id}/duplicate`, {})).data, t('apiService.toast.duplicated', { name: service.name }))
  /**
   * Tokens limited to what is being deleted (owner, 2026-10-06: a deleted service left its tokens
   * pointing at nothing, unnoticed). They keep the reference and call nothing, never widened to
   * everything; the confirm names them so they can be edited afterwards.
   */
  async function tokensLimitedTo(serviceId: string | null, endpointIds: string[]) {
    try {
      const tokens = (await api.list<ApiToken>('/api-tokens', { page_size: 100 }, { background: true })).data
      return tokens.filter(token => token.status !== 'revoked' && ((serviceId && token.scopes.services.includes(serviceId)) || token.scopes.endpoints.some(id => endpointIds.includes(id))))
    } catch {
      return []
    }
  }
  const tokensNote = (tokens: ApiToken[]) => (tokens.length ? ` ${t('apiService.delete.tokensNote', { n: tokens.length, names: tokens.map(token => token.name).join(', ') }, tokens.length)}` : '')
  async function deleteService(service: Pick<ApiService, 'id' | 'name' | 'endpoints_count'>) {
    const endpointIds = await api
      .list<ApiEndpoint>('/api-endpoints', { 'filter[service]': service.id, page_size: 100 }, { background: true })
      .then(result => result.data.map(item => item.id))
      .catch(() => [] as string[])
    const tokens = await tokensLimitedTo(service.id, endpointIds)
    const yes = await confirm({
      title: t('apiService.delete.serviceTitle', { name: service.name }),
      description: (service.endpoints_count ? t('apiService.delete.serviceDesc', { n: service.endpoints_count }, service.endpoints_count) : t('apiService.delete.serviceEmpty')) + tokensNote(tokens),
      confirmLabel: t('apiService.delete.confirm'),
      danger: true,
    })
    if (!yes) return false
    return !!(await act(service.id, () => api.del(`/api-services/${service.id}`), t('apiService.toast.serviceDeleted', { name: service.name })))
  }

  const setEndpointStatus = (endpoint: Pick<ApiEndpoint, 'id' | 'name'>, status: ApiStatus) =>
    act(endpoint.id, () => api.patch(`/api-endpoints/${endpoint.id}`, { status }), t(status === 'active' ? 'apiService.toast.endpointOn' : 'apiService.toast.endpointOff', { name: endpoint.name }))
  async function deleteEndpoint(endpoint: Pick<ApiEndpoint, 'id' | 'name'>) {
    const tokens = await tokensLimitedTo(null, [endpoint.id])
    const yes = await confirm({ title: t('apiService.delete.endpointTitle', { name: endpoint.name }), description: t('apiService.delete.endpointDesc') + tokensNote(tokens), confirmLabel: t('apiService.delete.confirm'), danger: true })
    if (!yes) return false
    return !!(await act(endpoint.id, () => api.del(`/api-endpoints/${endpoint.id}`), t('apiService.toast.endpointDeleted', { name: endpoint.name })))
  }
  function copyUrl(endpoint: Pick<ApiEndpoint, 'url'>) {
    void copy(endpoint.url)
    toast.add({ title: t('apiService.toast.urlCopied'), color: 'success', icon: 'i-lucide-check' })
  }

  return { busy, setServiceStatus, duplicateService, deleteService, setEndpointStatus, deleteEndpoint, copyUrl }
}
