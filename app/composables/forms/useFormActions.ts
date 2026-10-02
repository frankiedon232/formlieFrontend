import type { FormBulkAction, FormBulkResult, FormLifecycleAction, FormSummary } from '#shared/types/forms'

/**
 * Every action on forms in one place (list, grid, trash, detail): marks the form busy while it
 * runs (DataView `busy`), toasts the result, refreshes the list and the sidebar counts, and turns
 * a row_version conflict into "changed by someone else" + a fresh list (CLAUDE.md rules 4, 5, 13).
 */
export function useFormActions(onChanged: () => void | Promise<void>) {
  const { t } = useI18n()
  const api = useApi()
  const toast = useToast()
  const confirm = useConfirm()
  const { handle } = useErrorHandler()
  const counts = useNavCounts()

  const busyIds = ref(new Set<string>())
  const isBusy = (form: Pick<FormSummary, 'id'>) => busyIds.value.has(form.id)

  async function run<T>(ids: string[], action: () => Promise<T>, success?: string): Promise<T | undefined> {
    if (ids.some(id => busyIds.value.has(id))) return undefined
    busyIds.value = new Set([...busyIds.value, ...ids])
    try {
      const result = await action()
      if (success) toast.add({ title: success, color: 'success', icon: 'i-lucide-circle-check' })
      return result
    } catch (error) {
      handle(error)
      return undefined
    } finally {
      const next = new Set(busyIds.value)
      for (const id of ids) next.delete(id)
      busyIds.value = next
      // Also after a failure: a conflict means the list is stale.
      await onChanged()
      counts.refresh(true)
    }
  }

  const patch = (form: FormSummary, body: Record<string, unknown>, success: string) =>
    run([form.id], () => api.patch<FormSummary>(`/forms/${form.id}`, { row_version: form.row_version, ...body }), success)

  const rename = (form: FormSummary, name: string) =>
    name.trim() && name.trim() !== form.name
      ? patch(form, { name: name.trim() }, t('forms.toast.renamed'))
      : Promise.resolve(undefined)
  const move = (form: FormSummary, folderId: string | null) =>
    patch(form, { folder_id: folderId }, t('forms.toast.moved'))
  const setTags = (form: FormSummary, tags: string[]) => patch(form, { tags }, t('forms.toast.tagsSaved'))

  const duplicate = (form: FormSummary) =>
    run([form.id], () => api.post<FormSummary>(`/forms/${form.id}/duplicate`), t('forms.toast.duplicated'))

  const lifecycle = (form: FormSummary, action: FormLifecycleAction) =>
    run(
      [form.id],
      () => api.post<FormSummary>(`/forms/${form.id}/${action}`, { row_version: form.row_version }),
      t(`forms.toast.${action}`),
    )

  async function remove(form: FormSummary) {
    const ok = await confirm({
      title: t('forms.confirm.deleteTitle', { name: form.name }),
      description: t('forms.confirm.deleteDesc'),
      confirmLabel: t('forms.actions.delete'),
      danger: true,
    })
    if (ok) await run([form.id], () => api.del(`/forms/${form.id}`), t('forms.toast.deleted'))
  }

  async function purge(form: FormSummary) {
    const ok = await confirm({
      title: t('forms.confirm.purgeTitle', { name: form.name }),
      description: t('forms.confirm.purgeDesc'),
      confirmLabel: t('forms.actions.purge'),
      danger: true,
    })
    if (ok) await run([form.id], () => api.del(`/forms/${form.id}`, { query: { permanent: '1' } }), t('forms.toast.purged'))
  }

  /** Bulk action on selected forms; deletes ask first. Resolves true when it ran. */
  async function bulk(action: FormBulkAction, forms: FormSummary[], folderId?: string | null): Promise<boolean> {
    if (!forms.length) return false
    if (action === 'delete' || action === 'purge') {
      const ok = await confirm({
        title: t(`forms.confirm.bulk_${action}`, { count: forms.length }, forms.length),
        description: t(action === 'delete' ? 'forms.confirm.deleteDesc' : 'forms.confirm.purgeDesc'),
        confirmLabel: t(`forms.actions.${action}`),
        danger: true,
      })
      if (!ok) return false
    }
    const result = await run(
      forms.map(form => form.id),
      () => api.post<FormBulkResult>('/forms/bulk', { action, ids: forms.map(form => form.id), folder_id: folderId ?? null }),
    )
    if (!result) return false
    const { updated, failed } = result.data
    toast.add({
      title: t('forms.toast.bulk', { count: updated }, updated),
      description: failed.length ? t('forms.toast.bulkFailed', { count: failed.length }, failed.length) : undefined,
      color: failed.length ? 'warning' : 'success',
      icon: failed.length ? 'i-lucide-triangle-alert' : 'i-lucide-circle-check',
    })
    return true
  }

  async function emptyTrash(count: number) {
    const ok = await confirm({
      title: t('forms.confirm.emptyTitle'),
      description: t('forms.confirm.emptyDesc', { count }, count),
      confirmLabel: t('forms.trash.empty'),
      danger: true,
    })
    if (ok) await run(['__trash__'], () => api.del('/forms/trash'), t('forms.toast.emptied'))
  }

  return { busyIds, isBusy, rename, move, setTags, duplicate, lifecycle, remove, purge, bulk, emptyTrash }
}
