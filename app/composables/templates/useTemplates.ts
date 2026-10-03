import type { FormSummary } from '#shared/types/forms'
import type { TemplateCategorySummary, TemplateDetail, TemplateFacets, TemplateSummary } from '#shared/types/templates'

/**
 * Templates (F9): gallery data, "Use template" (new form → builder), duplicate, delete, save a
 * form as a workspace template. Names and Formalie templates' content come back in the person's
 * language (`lang`); a new form from a Formalie template starts in it.
 */
export function useTemplates() {
  const api = useApi()
  const toast = useToast()
  const { t, locale } = useI18n()
  const { handle } = useErrorHandler()

  const withLang = (params: Record<string, string | number> = {}) => ({ ...params, lang: locale.value })

  const list = (params: Record<string, string | number>, signal?: AbortSignal) =>
    api.list<TemplateSummary>('/templates', withLang(params), { signal })

  /** Formalie's categories with counts and use (the gallery's first level). */
  const categories = (params: Record<string, string | number>, signal?: AbortSignal) =>
    api.list<TemplateCategorySummary>('/templates/categories', withLang(params), { signal })

  const facets = async () => (await api.get<TemplateFacets>('/templates/facets', undefined, { background: true })).data

  const get = async (key: string) => (await api.get<TemplateDetail>(`/templates/${encodeURIComponent(key)}`, withLang())).data

  /** Create a form from the template and open it in the builder. */
  async function use(template: Pick<TemplateSummary, 'key' | 'name'>, input: { name: string; folder_id: string | null }) {
    try {
      const { data } = await api.post<FormSummary>('/forms', { ...input, template_key: template.key, language: locale.value })
      toast.add({ title: t('templates.toast.created', { name: data.name }), icon: 'i-lucide-file-plus', color: 'success' })
      await navigateTo(`/forms/${data.id}/build`)
      return data
    } catch (error) {
      handle(error)
      return null
    }
  }

  async function duplicate(template: Pick<TemplateSummary, 'key'>) {
    try {
      const { data } = await api.post<TemplateDetail>(`/templates/${encodeURIComponent(template.key)}/duplicate`, {}, { query: withLang() })
      toast.add({ title: t('templates.toast.duplicated', { name: data.name }), icon: 'i-lucide-copy', color: 'success' })
      return data
    } catch (error) {
      handle(error)
      return null
    }
  }

  async function remove(template: Pick<TemplateSummary, 'key' | 'name'>) {
    try {
      await api.del(`/templates/${encodeURIComponent(template.key)}`)
      toast.add({ title: t('templates.toast.deleted', { name: template.name }), icon: 'i-lucide-trash-2', color: 'success' })
      return true
    } catch (error) {
      handle(error)
      return false
    }
  }

  async function saveFromForm(input: { form_id: string; name: string; description: string; category: string }) {
    try {
      const { data } = await api.post<TemplateDetail>('/templates', input)
      void useNavCounts().refresh(true)
      toast.add({
        title: t('templates.toast.saved', { name: data.name }),
        icon: 'i-lucide-layout-template',
        color: 'success',
        actions: [{ label: t('templates.view'), to: `/templates/${data.key}` }],
      })
      return data
    } catch (error) {
      handle(error)
      return null
    }
  }

  async function update(key: string, patch: { name?: string; description?: string; category?: string }) {
    try {
      const { data } = await api.patch<TemplateDetail>(`/templates/${encodeURIComponent(key)}`, patch)
      toast.add({ title: t('templates.toast.updated', { name: data.name }), icon: 'i-lucide-circle-check', color: 'success' })
      return data
    } catch (error) {
      handle(error)
      return null
    }
  }

  return { list, categories, facets, get, use, duplicate, remove, saveFromForm, update }
}
