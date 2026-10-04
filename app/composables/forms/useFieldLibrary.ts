import type { OptionList, SavedField } from '#shared/types/forms'
import type { FormField } from '#shared/utils/forms/build'

// Shared by the palette, the inspector and the list manager on the same page (workspace data,
// no secrets, a plain module-level cache that each builder visit refreshes).
const savedFields = ref<SavedField[]>([])
const lists = ref<OptionList[]>([])
const loading = ref(false)
const loaded = ref(false)

/**
 * Reusable building blocks (owner request, F7): fields saved from the inspector, and option lists
 * (countries, regions, products …) that fill any choice field. Every change is audited server-side.
 */
export function useFieldLibrary() {
  const api = useApi()
  const toast = useToast()
  const { t } = useI18n()
  const { handle } = useErrorHandler()

  async function load(force = false) {
    if (loading.value || (loaded.value && !force)) return
    loading.value = true
    try {
      const [fields, optionLists] = await Promise.all([
        api.get<SavedField[]>('/field-library', undefined, { background: true }),
        api.get<OptionList[]>('/option-lists', undefined, { background: true }),
      ])
      savedFields.value = fields.data
      lists.value = optionLists.data
      loaded.value = true
    } catch (error) {
      handle(error)
    } finally {
      loading.value = false
    }
  }

  async function saveField(name: string, field: FormField): Promise<boolean> {
    try {
      const { id: _id, ...rest } = structuredClone(toRaw(field))
      const { data } = await api.post<SavedField>('/field-library', { name, field: rest })
      savedFields.value = [...savedFields.value, data].sort((a, b) => a.name.localeCompare(b.name))
      toast.add({ title: t('library.toast.fieldSaved', { name }), icon: 'i-lucide-bookmark-check', color: 'success' })
      return true
    } catch (error) {
      handle(error)
      return false
    }
  }

  async function removeField(item: SavedField): Promise<boolean> {
    try {
      await api.del(`/field-library/${item.id}`)
      savedFields.value = savedFields.value.filter(f => f.id !== item.id)
      toast.add({ title: t('library.toast.fieldRemoved', { name: item.name }), icon: 'i-lucide-bookmark-minus', color: 'neutral' })
      return true
    } catch (error) {
      handle(error)
      return false
    }
  }

  async function saveList(input: { name: string; options: OptionList['options'] }, id?: string): Promise<OptionList | null> {
    try {
      const { data } = id
        ? await api.patch<OptionList>(`/option-lists/${id}`, input)
        : await api.post<OptionList>('/option-lists', input)
      lists.value = [...lists.value.filter(l => l.id !== data.id), data].sort((a, b) => a.name.localeCompare(b.name))
      toast.add({ title: t(id ? 'library.toast.listUpdated' : 'library.toast.listCreated', { name: data.name }), icon: 'i-lucide-list-checks', color: 'success' })
      return data
    } catch (error) {
      handle(error)
      return null
    }
  }

  async function removeList(item: OptionList): Promise<boolean> {
    try {
      await api.del(`/option-lists/${item.id}`)
      lists.value = lists.value.filter(l => l.id !== item.id)
      toast.add({ title: t('library.toast.listDeleted', { name: item.name }), icon: 'i-lucide-list-x', color: 'neutral' })
      return true
    } catch (error) {
      handle(error)
      return false
    }
  }

  return { savedFields, lists, loading, loaded, load, saveField, removeField, saveList, removeList }
}
