/**
 * One Settings page's form (F14): a draft of its section, what changed, field errors from the shared
 * rules (shown once someone saved or left a field), Save (PATCH, toast, audit on the server) and
 * Discard, Ctrl / ⌘ + S, and a warning before leaving (or closing the tab) with unsaved changes.
 */
import type { ZodType } from 'zod'
import type { SettingsSection, WorkspaceSettings } from '#shared/types/settings'

const KNOWN = new Set(['website', 'email', 'phone', 'country', 'color', 'timezone', 'currency', 'form_languages', 'methods', 'domain', 'ip', 'ip_empty', 'people', 'subject', 'body'])

export function useSettingsForm<S extends SettingsSection>(section: S, options: { schema?: ZodType; body?: (draft: WorkspaceSettings[S]) => unknown; beforeSave?: () => Promise<boolean> } = {}) {
  const { t } = useI18n()
  const api = useApi()
  const toast = useToast()
  const confirm = useConfirm()
  const session = useSession()
  const { handle } = useErrorHandler()
  const store = useWorkspaceSettings()

  const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T
  const draft = ref(null) as Ref<WorkspaceSettings[S] | null>
  const saved = computed(() => store.settings.value?.[section] ?? null)
  const updated = computed(() => store.settings.value?.updated[section] ?? null)
  watch(saved, value => value && !draft.value && (draft.value = clone(value)), { immediate: true })
  onMounted(() => void store.load().catch(() => {}))

  const dirty = computed(() => !!draft.value && !!saved.value && JSON.stringify(draft.value) !== JSON.stringify(saved.value))
  const touched = ref(false)
  /** Field errors by path ("address.city"), in words. */
  const errors = computed<Record<string, string>>(() => {
    if (!options.schema || !draft.value) return {}
    const result = options.schema.safeParse(draft.value)
    if (result.success) return {}
    return Object.fromEntries(result.error.issues.map(issue => [issue.path.join('.'), t(`settings.invalid.${KNOWN.has(issue.message) ? issue.message : issue.code}`)]))
  })
  const errorOf = (path: string) => (touched.value ? errors.value[path] : undefined)

  const saving = ref(false)
  async function save() {
    if (!draft.value || saving.value) return false
    touched.value = true
    if (Object.keys(errors.value).length) {
      toast.add({ title: t('settings.fixErrors'), color: 'warning', icon: 'i-lucide-triangle-alert' })
      return false
    }
    // A last question before saving (e.g. Privacy: responses a shorter limit removes)
    if (options.beforeSave && !(await options.beforeSave())) return false
    saving.value = true
    try {
      const { data } = await api.patch<WorkspaceSettings[S]>(`/settings/${section}`, options.body ? options.body(draft.value) : draft.value)
      const user = session.user.value
      store.put(section, data, user ? `${user.first_name} ${user.last_name}` : '')
      draft.value = clone(data)
      touched.value = false
      toast.add({ title: t('settings.saved'), color: 'success', icon: 'i-lucide-circle-check' })
      return true
    } catch (error) {
      handle(error)
      return false
    } finally {
      saving.value = false
    }
  }
  function discard() {
    if (saved.value) draft.value = clone(saved.value)
    touched.value = false
  }

  defineShortcuts({ meta_s: { usingInput: true, handler: () => void save() } })
  onBeforeRouteLeave(async () => (!dirty.value ? true : await confirm({ title: t('settings.leave.title'), description: t('settings.leave.desc'), confirmLabel: t('settings.leave.confirm'), danger: true })))
  useEventListener(window, 'beforeunload', event => {
    if (dirty.value) event.preventDefault()
  })

  return { draft, saved, updated, dirty, saving, errors, errorOf, save, discard, failed: store.failed, reload: () => store.load(true) }
}
