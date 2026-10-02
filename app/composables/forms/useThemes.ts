import type { SavedTheme } from '#shared/types/forms'
import type { FormTheme } from '#shared/utils/forms/theme'

// Shared by the designer and the themes page (workspace data, no secrets).
const themes = ref<SavedTheme[]>([])
const loading = ref(false)
const loaded = ref(false)

/** Saved designs (F8): save from a form, apply to any form, rename / duplicate / delete. */
export function useThemes() {
  const api = useApi()
  const toast = useToast()
  const { t } = useI18n()
  const { handle } = useErrorHandler()

  async function load(force = false) {
    if (loading.value || (loaded.value && !force)) return
    loading.value = true
    try {
      themes.value = (await api.list<SavedTheme>('/themes', { page_size: 100 }, { background: true })).data
      loaded.value = true
    } catch (error) {
      handle(error)
    } finally {
      loading.value = false
    }
  }

  const upsert = (theme: SavedTheme) => (themes.value = [theme, ...themes.value.filter(item => item.id !== theme.id)])

  async function create(name: string, tokens: FormTheme): Promise<SavedTheme | null> {
    try {
      const { data } = await api.post<SavedTheme>('/themes', { name, tokens })
      upsert(data)
      toast.add({ title: t('themes.toast.saved', { name: data.name }), icon: 'i-lucide-palette', color: 'success' })
      return data
    } catch (error) {
      handle(error)
      return null
    }
  }

  async function update(id: string, patch: { name?: string; tokens?: FormTheme }): Promise<SavedTheme | null> {
    try {
      const { data } = await api.patch<SavedTheme>(`/themes/${id}`, patch)
      upsert(data)
      toast.add({ title: t('themes.toast.updated', { name: data.name }), icon: 'i-lucide-circle-check', color: 'success' })
      return data
    } catch (error) {
      handle(error)
      return null
    }
  }

  async function duplicate(theme: SavedTheme): Promise<SavedTheme | null> {
    try {
      const { data } = await api.post<SavedTheme>(`/themes/${theme.id}/duplicate`)
      upsert(data)
      toast.add({ title: t('themes.toast.duplicated', { name: data.name }), icon: 'i-lucide-copy', color: 'success' })
      return data
    } catch (error) {
      handle(error)
      return null
    }
  }

  async function remove(theme: SavedTheme): Promise<boolean> {
    try {
      await api.del(`/themes/${theme.id}`)
      themes.value = themes.value.filter(item => item.id !== theme.id)
      toast.add({ title: t('themes.toast.deleted', { name: theme.name }), icon: 'i-lucide-trash-2', color: 'neutral' })
      return true
    } catch (error) {
      handle(error)
      return false
    }
  }

  return { themes, loading, loaded, load, create, update, duplicate, remove }
}
