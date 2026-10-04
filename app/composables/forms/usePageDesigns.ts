import type { PageDesign } from '#shared/types/forms'
import type { PageDesignTokens } from '#shared/utils/forms/page-design'

// Shared by the designers and the Pages library (workspace data, no secrets).
const pages = ref<PageDesign[]>([])
const loading = ref(false)
const loaded = ref(false)

/**
 * Page designs (Resources → Landing pages, owner 2026-10-04): the page around a form on its public link.
 * Load every design (Formalie's and the workspace's) for pickers, save from a form, create in the
 * page editor, rename / duplicate / delete, like Themes.
 */
export function usePageDesigns() {
  const api = useApi()
  const toast = useToast()
  const { t, te } = useI18n()
  const { handle } = useErrorHandler()
  const counts = useNavCounts()

  async function load(force = false) {
    if (loading.value || (loaded.value && !force)) return
    loading.value = true
    try {
      pages.value = (await api.list<PageDesign>('/page-designs', { page_size: 100, sort: 'name' }, { background: true })).data
      loaded.value = true
    } catch (error) {
      handle(error)
    } finally {
      loading.value = false
    }
  }

  const upsert = (page: PageDesign) => {
    pages.value = [page, ...pages.value.filter(item => item.id !== page.id)]
    void counts.refresh(true)
  }

  /** `saved` from a form's design · `created` in the page editor. */
  async function create(name: string, tokens: PageDesignTokens, source: 'saved' | 'created' = 'saved'): Promise<PageDesign | null> {
    try {
      const { data } = await api.post<PageDesign>('/page-designs', { name, tokens, source })
      upsert(data)
      toast.add({ title: t('pages.toast.saved', { name: data.name }), icon: 'i-lucide-panels-top-left', color: 'success' })
      return data
    } catch (error) {
      handle(error)
      return null
    }
  }

  async function update(id: string, patch: { name?: string; tokens?: PageDesignTokens }): Promise<PageDesign | null> {
    try {
      const { data } = await api.patch<PageDesign>(`/page-designs/${id}`, patch)
      upsert(data)
      toast.add({ title: t('pages.toast.updated', { name: data.name }), icon: 'i-lucide-circle-check', color: 'success' })
      return data
    } catch (error) {
      handle(error)
      return null
    }
  }

  async function duplicate(page: Pick<PageDesign, 'id' | 'name'>): Promise<PageDesign | null> {
    try {
      const { data } = await api.post<PageDesign>(`/page-designs/${page.id}/duplicate`, { name: `${page.name} (${t('themes.copySuffix')})` })
      upsert(data)
      toast.add({ title: t('pages.toast.duplicated', { name: data.name }), icon: 'i-lucide-copy', color: 'success' })
      return data
    } catch (error) {
      handle(error)
      return null
    }
  }

  async function remove(page: PageDesign): Promise<boolean> {
    try {
      await api.del(`/page-designs/${page.id}`)
      pages.value = pages.value.filter(item => item.id !== page.id)
      void counts.refresh(true)
      toast.add({ title: t('pages.toast.deleted', { name: page.name }), icon: 'i-lucide-trash-2', color: 'neutral' })
      return true
    } catch (error) {
      handle(error)
      return false
    }
  }

  const get = async (id: string) => (await api.get<PageDesign>(`/page-designs/${encodeURIComponent(id)}`)).data

  /** Formalie's designs show their name in the person's language; others as written. */
  const nameOf = (page: Pick<PageDesign, 'name' | 'name_key'>) => (page.name_key && te(page.name_key) ? t(page.name_key) : page.name)

  return { pages, loading, loaded, load, create, update, duplicate, remove, get, nameOf }
}
