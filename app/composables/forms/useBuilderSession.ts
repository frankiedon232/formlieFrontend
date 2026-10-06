import type { InjectionKey } from 'vue'
import type { FormSummary } from '#shared/types/forms'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'

/**
 * Everything the builder, logic and versions pages share for one form: load, the builder
 * state (provided to children), autosave, inline rename, publish, discard and the
 * "Saved just now" line. Each page calls this once and renders <FormsBuilderFrame>.
 */
export function useBuilderSession(formId: string) {
  const { t } = useI18n()
  const api = useApi()
  const toast = useToast()
  const { handle } = useErrorHandler()
  const { setLabel } = useBreadcrumbs()
  const { relative } = useFormat()
  const counts = useNavCounts()

  const builder = useFormBuilder()
  provideFormBuilder(builder)

  const form = ref<FormSummary | null>(null)
  const rowVersion = ref(0)
  const loading = ref(true)
  const failed = ref<string | null>(null)
  /** May change this form (people access, decision 97). The server refuses the editor to anyone else; this is the backstop. */
  const canEdit = computed(() => !form.value || canEditForm(form.value))

  const autosave = useBuilderAutosave(formId, builder.schema, rowVersion, saved => {
    if (form.value)
      Object.assign(form.value, { has_unpublished_changes: saved.has_unpublished_changes, updated_at: saved.updated_at })
  })

  function apply(next: FormSummary, schema?: FormSchemaV1) {
    form.value = next
    rowVersion.value = next.row_version
    if (schema) {
      if (canEdit.value) autosave.start()
      builder.load(schema)
    }
  }

  async function load() {
    loading.value = true
    failed.value = null
    try {
      const { data } = await api.get<{ form: FormSummary; schema: FormSchemaV1; published_version: number | null; published_keys?: string[]; live_fields?: { key: string; label: string; required: boolean; type: string }[] }>(
        `/forms/${formId}/builder`,
      )
      apply(data.form, data.schema)
      // Keys a published version used stay fixed; the rest follow their labels (clean keys)
      builder.liveFields.value = data.live_fields ?? []
      builder.publishedKeys.value = new Set(data.published_keys ?? (data.form.status !== 'draft' || data.published_version !== null ? allFields(data.schema).map(field => field.key) : []))
      setLabel(`/forms/${formId}`, data.form.name)
    } catch (error) {
      failed.value = handle(error, { silent: true }).code
    } finally {
      loading.value = false
    }
  }

  /** Inline rename, waits for autosave so the two never race on row_version. */
  async function rename(name: string): Promise<boolean> {
    if (!form.value || !name.trim() || name.trim() === form.value.name) return false
    await until(autosave.state).not.toBe('saving')
    try {
      const { data } = await api.patch<FormSummary>(`/forms/${formId}`, { row_version: rowVersion.value, name: name.trim() })
      apply({ ...form.value, ...data })
      setLabel(`/forms/${formId}`, data.name)
      return true
    } catch (error) {
      handle(error)
      return false
    }
  }

  const { busy: publishing, run } = useBusy()
  async function publish(summary: string | null): Promise<boolean> {
    await autosave.saveNow()
    const result = await run(() =>
      api.post<{ form: FormSummary; version: { number: number } }>(`/forms/${formId}/publish`, {
        row_version: rowVersion.value,
        change_summary: summary,
      }),
    )
    if (!result) return false
    apply(result.data.form)
    builder.publishedKeys.value = new Set([...builder.publishedKeys.value, ...builder.fields.value.map(field => field.key)])
    builder.liveFields.value = builder.fields.value.filter(field => field.key).map(field => ({ key: field.key, label: field.label ?? '', required: !!field.required, type: field.type }))
    counts.refresh(true)
    toast.add({ title: t('builder.publish.done', { n: result.data.version.number }), icon: 'i-lucide-globe', color: 'success' })
    return true
  }

  /** Replace the draft from the server (restore a version, discard changes). */
  async function replaceDraft(path: string, success: string): Promise<boolean> {
    await until(autosave.state).not.toBe('saving')
    const result = await run(() => api.post<{ form: FormSummary; schema: FormSchemaV1 }>(path))
    if (!result) return false
    apply(result.data.form, result.data.schema)
    toast.add({ title: success, icon: 'i-lucide-circle-check', color: 'success' })
    return true
  }

  // "Saved 2 minutes ago" stays current without re-rendering every second.
  const now = ref(Date.now())
  useIntervalFn(() => (now.value = Date.now()), 15_000)
  const statusText = computed(() => {
    const s = autosave.state.value
    if (s === 'saving' || s === 'pending') return t('builder.save.saving')
    if (s === 'error') return t('builder.save.error')
    if (s === 'conflict') return t('builder.save.conflict')
    return autosave.savedAt.value
      ? t('builder.save.saved', { time: relative(autosave.savedAt.value, Math.max(now.value, autosave.savedAt.value)) })
      : t('builder.save.upToDate')
  })

  // Full screen: only fields · canvas · settings with a slim bar (FormsBuilderFrame). Uses the
  // browser's full screen when allowed; leaving it (Esc) leaves our mode too.
  const fullscreen = ref(false)
  const browser = useFullscreen()
  async function toggleFullscreen(next = !fullscreen.value) {
    fullscreen.value = next
    try {
      if (next && browser.isSupported.value) await browser.enter()
      else if (!next && browser.isFullscreen.value) await browser.exit()
    } catch {
      // Not allowed (e.g. inside an iframe): the in-app full screen still works.
    }
  }
  watch(browser.isFullscreen, active => {
    if (!active && fullscreen.value) fullscreen.value = false
  })
  onBeforeRouteLeave(() => {
    if (fullscreen.value) void toggleFullscreen(false)
  })

  onMounted(load)

  return {
    formId, builder, form, rowVersion, loading, failed, autosave, statusText, publishing, canEdit,
    fullscreen, toggleFullscreen, load, rename, publish, replaceDraft,
  }
}

export type BuilderSession = ReturnType<typeof useBuilderSession>

const SESSION_KEY: InjectionKey<BuilderSession> = Symbol('builder-session')
/** The builder frame shares its session (form id, autosave) with the panels inside it. */
export const provideBuilderSession = (session: BuilderSession) => provide(SESSION_KEY, session)
export const injectBuilderSession = () => inject(SESSION_KEY, null)
