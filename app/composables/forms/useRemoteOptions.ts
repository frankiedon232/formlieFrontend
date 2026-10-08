/**
 * Long lists on the public page (F15 M3): a choice field whose options stayed on the server asks for
 * matches as people type (a short pause first), shows the first 50 and how many match in all, and keeps
 * the labels of what was chosen (a resumed draft asks for those by value). Fields with their options
 * (builder, previews, shorter lists) do nothing here.
 */
import type { FormField } from '#shared/utils/forms/build'

type Item = { value: string; label: string }

export function useRemoteOptions(field: () => FormField, chosen: () => string[]) {
  const lookup = inject(RENDERER_LOOKUP, null)
  const remote = computed(() => !!field().options_remote && !!lookup)
  const term = ref('')
  const found = ref<Item[]>([])
  const total = ref(0)
  const loading = ref(false)
  const failed = ref(false)
  const labels = ref<Record<string, string>>({})

  async function search(q: string) {
    if (!remote.value) return
    loading.value = true
    failed.value = false
    try {
      const result = await lookup!(field().key, q.trim())
      found.value = result.items
      total.value = result.total
      for (const item of result.items) labels.value[item.value] = item.label
    } catch {
      failed.value = true
      found.value = []
    } finally {
      loading.value = false
    }
  }
  watchDebounced(term, q => void search(q), { debounce: 250 })
  onMounted(() => void search(''))

  // Labels of chosen options not seen yet (a resumed draft)
  watch(
    chosen,
    async values => {
      const missing = values.filter(value => !(value in labels.value))
      if (!remote.value || !missing.length) return
      try {
        const result = await lookup!(field().key, '', missing)
        for (const item of result.items) labels.value[item.value] = item.label
      } catch {
        // The value shows until the label arrives
      }
    },
    { immediate: true },
  )

  /** The matches, plus what was chosen (so the control can show it even when it doesn't match). */
  const items = computed<Item[]>(() => {
    const list = [...found.value]
    for (const value of chosen()) if (!list.some(item => item.value === value)) list.push({ value, label: labels.value[value] ?? value })
    return list
  })
  return { remote, term, items, total, loading, failed, retry: () => search(term.value) }
}
