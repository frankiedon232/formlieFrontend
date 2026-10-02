import type { FormSchemaV1 } from '#shared/utils/forms/schema'

export type SaveState = 'idle' | 'pending' | 'saving' | 'saved' | 'error' | 'conflict'

interface DraftSaved {
  row_version: number
  updated_at: string
  has_unpublished_changes: boolean
}

/**
 * Autosave for the builder draft (FRONTEND-SPEC §6): debounced PUT /forms/:id/draft with the
 * row_version; a conflict stops saving and asks to reload instead of overwriting someone else's
 * work. Shows its own "Saving… / Saved" line, so it doesn't drive the page progress bars.
 */
export function useBuilderAutosave(
  formId: string,
  schema: Ref<FormSchemaV1 | null>,
  rowVersion: Ref<number>,
  onSaved: (result: DraftSaved) => void,
) {
  const api = useApi()
  const { handle } = useErrorHandler()
  const state = ref<SaveState>('idle')
  const savedAt = ref<number | null>(null)
  let paused = true
  let again = false

  async function save() {
    if (!schema.value || state.value === 'conflict') return
    if (state.value === 'saving') {
      again = true
      return
    }
    state.value = 'saving'
    try {
      const { data } = await api.put<DraftSaved>(
        `/forms/${formId}/draft`,
        { row_version: rowVersion.value, schema: toRaw(schema.value) },
        { background: true },
      )
      rowVersion.value = data.row_version
      savedAt.value = Date.now()
      state.value = 'saved'
      onSaved(data)
    } catch (error) {
      const normalised = handle(error, { silent: true })
      state.value = normalised.code === 'FRM-GEN-1009' ? 'conflict' : 'error'
      if (state.value === 'error') handle(error)
    } finally {
      if (again && state.value === 'saved') {
        again = false
        save()
      }
    }
  }

  const debounced = useDebounceFn(save, 1000)

  watch(
    schema,
    () => {
      if (paused || state.value === 'conflict') return
      state.value = 'pending'
      debounced()
    },
    { deep: true },
  )

  /** Start watching after the first load (so loading isn't saved back). */
  function start() {
    nextTick(() => (paused = false))
  }

  const unsaved = computed(
    () => state.value === 'pending' || state.value === 'saving' || state.value === 'error',
  )
  useEventListener(window, 'beforeunload', event => {
    if (unsaved.value) event.preventDefault()
  })

  return { state, savedAt, unsaved, saveNow: save, start }
}
