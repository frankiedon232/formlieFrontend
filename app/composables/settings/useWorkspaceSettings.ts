/**
 * The workspace's settings (F14), loaded once and shared by every Settings page and the overview;
 * a save puts the new section in place so all of them show it at once.
 */
import type { SettingsSection, WorkspaceSettings } from '#shared/types/settings'

const settings = ref<WorkspaceSettings | null>(null)
const failed = ref(false)
let loading: Promise<void> | null = null

export function useWorkspaceSettings() {
  const api = useApi()
  function load(force = false) {
    if (loading && !force) return loading
    failed.value = false
    loading = api
      .get<WorkspaceSettings>('/settings')
      .then(result => void (settings.value = result.data))
      .catch(error => {
        failed.value = true
        loading = null
        throw error
      })
    return loading
  }
  function put<S extends SettingsSection>(section: S, value: WorkspaceSettings[S], by: string) {
    if (!settings.value) return
    settings.value = { ...settings.value, [section]: value, updated: { ...settings.value.updated, [section]: { at: new Date().toISOString(), by } } }
  }
  return { settings, failed, load, put }
}
