/**
 * The workspace's AI assistant settings (F19), loaded once and shared by every assistant page, the
 * overview and (later) the in-context helpers in the builder, templates and responses. Saving goes
 * through the API; the result replaces the shared copy so every place follows at once.
 */
import type { AiSettings, AiSource } from '#shared/types/ai'

export function useAi() {
  const api = useApi()
  const { handle } = useErrorHandler()
  const settings = useState<AiSettings | null>('ai-settings', () => null)
  const failed = useState('ai-settings-failed', () => false)
  const loading = ref(false)

  async function load(force = false) {
    if (settings.value && !force) return settings.value
    loading.value = true
    failed.value = false
    try {
      settings.value = (await api.get<AiSettings>('/ai/settings')).data
    } catch (error) {
      failed.value = true
      handle(error, { silent: true })
    } finally {
      loading.value = false
    }
    return settings.value
  }

  async function save(patch: Partial<Pick<AiSettings, 'enabled' | 'mask_personal' | 'keep_days'>> & { sources?: Partial<AiSettings['sources']> }) {
    settings.value = (await api.patch<AiSettings>('/ai/settings', patch)).data
    return settings.value
  }

  /** On until the settings say otherwise (so pages don't flash the switched-off state while loading). */
  const enabled = computed(() => settings.value?.enabled ?? true)
  /** The first part this page needs that the workspace keeps from the assistant (null = all allowed or not loaded yet). */
  const blocked = (...needs: AiSource[]) => needs.find(source => settings.value?.sources[source] === false) ?? null

  return { settings, loading, failed, load, save, enabled, blocked }
}
