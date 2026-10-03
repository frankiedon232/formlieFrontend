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
      // The designer's "Your themes": the workspace's own (system designs are its starting points).
      themes.value = (await api.list<SavedTheme>('/themes', { page_size: 100, 'filter[source]': 'saved,created' }, { background: true })).data
      loaded.value = true
    } catch (error) {
      handle(error)
    } finally {
      loading.value = false
    }
  }

  const upsert = (theme: SavedTheme) => (themes.value = [theme, ...themes.value.filter(item => item.id !== theme.id)])

  /** `saved` from a form's design (designer) · `created` in the theme editor. */
  async function create(name: string, tokens: FormTheme, source: 'saved' | 'created' = 'saved'): Promise<SavedTheme | null> {
    try {
      const { data } = await api.post<SavedTheme>('/themes', { name, tokens, source })
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

  async function duplicate(theme: Pick<SavedTheme, 'id' | 'name'>): Promise<SavedTheme | null> {
    try {
      // The name as shown (system themes in the person's language) becomes the copy's name.
      const { data } = await api.post<SavedTheme>(`/themes/${theme.id}/duplicate`, { name: `${theme.name} (${t('themes.copySuffix')})` })
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

  /** One theme (system ones included) — the theme editor. */
  const get = async (id: string) => (await api.get<SavedTheme>(`/themes/${encodeURIComponent(id)}`)).data

  /** System themes show their name in the person's language; others as written. */
  const { te } = useI18n()
  const nameOf = (theme: Pick<SavedTheme, 'name' | 'name_key' | 'id'>) => {
    if (!theme.name_key || !te(theme.name_key)) return theme.name
    return theme.id.startsWith('sys_category_') ? t('themes.categoryDesign', { name: t(theme.name_key) }) : t(theme.name_key)
  }

  return { themes, loading, loaded, load, create, update, duplicate, remove, get, nameOf }
}
