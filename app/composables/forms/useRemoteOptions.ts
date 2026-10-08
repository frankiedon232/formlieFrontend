/**
 * Options that stay on the server (F15 M3 long lists, F15 M5 large lists): the field asks for matches as
 * people type (a short pause first), shows the first 50 and how many match in all, and keeps the labels
 * of what was chosen (a resumed draft asks for those by value). A lower level of a large list asks only
 * for what is under the choice above, and drops chosen options that no longer fit when that choice
 * changes. The public page provides its lookup (RENDERER_LOOKUP); the builder and previews ask the list.
 * Fields that carry their options do nothing here.
 */
import type { FormField } from '#shared/utils/forms/build'
import type { RendererLookup } from '#shared/types/public'

type Item = { value: string; label: string; attrs?: Record<string, string | number> }

/** The builder and previews: a large list's options from the list itself (signed in). */
function useListLookup(): RendererLookup {
  const api = useApi()
  return async (field, query) => {
    if (!field.option_set_id) return { items: [], total: 0 }
    const params = { level: field.option_level ?? 0, q: query.q, ...(query.values?.length ? { values: query.values.join(',') } : {}), ...(query.parents ? { parents: query.parents.join(',') } : {}) }
    return (await api.get<{ items: Item[]; total: number }>(`/option-lists/${field.option_set_id}/options`, params, { background: true })).data
  }
}

export function useRemoteOptions(field: () => FormField, chosen: () => string[], setChosen: (values: string[]) => void) {
  const lookup = inject(RENDERER_LOOKUP, null) ?? useListLookup()
  const live = inject(RENDERER_ANSWERS, null)
  const remote = computed(() => (!!field().options_remote || !!field().options_large) && !field().options?.length)
  // The choices one level up (large lists only ask for what is under them)
  const parents = computed<string[] | undefined>(() => {
    const above = field().option_parent ? live?.fieldsById.value.get(field().option_parent!) : undefined
    if (!above) return undefined
    const value = live!.answers.value[above.key]
    return (Array.isArray(value) ? value : value ? [value] : []).filter((item): item is string => typeof item === 'string')
  })
  const term = ref('')
  const found = ref<Item[]>([])
  const total = ref(0)
  const loading = ref(false)
  const failed = ref(false)
  const labels = ref<Record<string, string>>({})
  // Details of options seen, for auto-fill (the form keeps those of chosen options)
  const seen = new Map<string, Item>()
  const remember = (items: Item[]) => {
    for (const item of items) {
      labels.value[item.value] = item.label
      seen.set(item.value, item)
    }
    keepPicked(chosen())
  }
  function keepPicked(values: string[]) {
    if (!live?.picked) return
    const id = field().id
    const kept = live.picked.value[id] ?? []
    const fresh = values.filter(value => seen.has(value) && !kept.some(item => item.value === value)).map(value => seen.get(value)!)
    if (fresh.length) live.picked.value = { ...live.picked.value, [id]: [...kept, ...fresh] }
  }

  async function search(q: string) {
    if (!remote.value) return
    if (parents.value && !parents.value.length) return ((found.value = []), (total.value = 0))
    loading.value = true
    failed.value = false
    try {
      const result = await lookup(field(), { q: q.trim(), parents: parents.value })
      found.value = result.items
      total.value = result.total
      remember(result.items)
    } catch {
      failed.value = true
      found.value = []
    } finally {
      loading.value = false
    }
  }
  watchDebounced(term, q => void search(q), { debounce: 250 })
  onMounted(() => void search(''))

  // The choice above changed: search again, and keep only what is still under it
  watch(
    () => parents.value?.join('\u001f'),
    async (now, before) => {
      if (!remote.value || now === before) return
      term.value = ''
      void search('')
      const values = chosen()
      if (!values.length) return
      if (!parents.value?.length) return setChosen([])
      try {
        const result = await lookup(field(), { q: '', values, parents: parents.value })
        const kept = new Set(result.items.map(item => item.value))
        if (values.some(value => !kept.has(value))) setChosen(values.filter(value => kept.has(value)))
      } catch {
        // The server checks it on submit
      }
    },
  )

  // Labels of chosen options not seen yet (a resumed draft)
  watch(
    chosen,
    async values => {
      keepPicked(values)
      const missing = values.filter(value => !(value in labels.value))
      if (!remote.value || !missing.length) return
      try {
        const result = await lookup(field(), { q: '', values: missing, parents: parents.value })
        remember(result.items)
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
