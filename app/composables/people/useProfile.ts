/**
 * My profile (F16 M5): the person's own profile, loaded once per page, saved in parts (details,
 * preferences, notifications) with the button busy meanwhile. Name, photo and preferences also update
 * the signed-in user at once (menu avatar, dates in their time zone and format).
 */
import type { MyProfile } from '#shared/types/profile'

export function useProfile() {
  const { t } = useI18n()
  const api = useApi()
  const toast = useToast()
  const session = useSession()
  const { handle } = useErrorHandler()
  const profile = useState<MyProfile | null>('my-profile', () => null)
  const failed = ref(false)
  const saving = ref<string | null>(null)

  async function load() {
    failed.value = false
    try {
      profile.value = (await api.get<MyProfile>('/me/profile')).data
    } catch {
      failed.value = true
    }
  }

  /** Saves part of the profile; `part` names the busy button. */
  async function save(part: string, values: Partial<MyProfile>, message = t('profile.saved')) {
    if (saving.value) return false
    saving.value = part
    try {
      profile.value = (await api.patch<MyProfile>('/me/profile', values)).data
      const p = profile.value
      session.updateUser({ first_name: p.first_name, last_name: p.last_name, avatar_url: p.photo, language: p.language, time_zone: p.time_zone, date_format: p.date_format })
      toast.add({ title: message, color: 'success', icon: 'i-lucide-circle-check' })
      return true
    } catch (error) {
      handle(error)
      return false
    } finally {
      saving.value = null
    }
  }

  return { profile, failed, saving, load, save }
}
