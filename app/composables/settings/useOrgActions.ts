/**
 * Actions on organisation entries (F14 M2): archive and restore (a toast confirms), delete (asks first;
 * refused while forms use it, and then says to archive or merge instead). The entry being changed is
 * marked busy so its row or card shows a spinner. `done` refreshes the page.
 */
import type { OrgItem, OrgKind } from '#shared/types/org'

export const SETTINGS_ORG_ICONS: Record<OrgKind, string> = {
  departments: 'i-lucide-network',
  job_titles: 'i-lucide-id-card',
}

export function useOrgActions(kind: MaybeRefOrGetter<OrgKind>, done: () => unknown) {
  const { t } = useI18n()
  const api = useApi()
  const toast = useToast()
  const confirm = useConfirm()
  const { handle } = useErrorHandler()
  const busy = ref<string | null>(null)

  async function act(item: OrgItem, work: () => Promise<unknown>, message: string) {
    if (busy.value) return false
    busy.value = item.id
    try {
      await work()
      toast.add({ title: message, color: 'success', icon: 'i-lucide-circle-check' })
      await done()
      return true
    } catch (error) {
      handle(error)
      return false
    } finally {
      busy.value = null
    }
  }
  const base = () => `/org/${toValue(kind)}`
  const archive = (item: OrgItem) => act(item, () => api.post(`${base()}/${item.id}/archive`), t('settings.org.toast.archived', { name: item.name }))
  const restore = (item: OrgItem) => act(item, () => api.post(`${base()}/${item.id}/restore`), t('settings.org.toast.restored', { name: item.name }))
  async function remove(item: OrgItem) {
    if (item.forms_count) {
      toast.add({ title: t('errors.FRM-ORG-1002'), description: t('settings.org.inUseBy', { n: item.forms_count }, item.forms_count), color: 'warning', icon: 'i-lucide-lock' })
      return false
    }
    if (!(await confirm({ title: t('settings.org.deleteTitle', { name: item.name }), description: t('settings.org.deleteDesc'), confirmLabel: t('apiService.delete.confirm'), danger: true }))) return false
    return act(item, () => api.del(`${base()}/${item.id}`), t('settings.org.toast.deleted', { name: item.name }))
  }
  return { busy, archive, restore, remove }
}
