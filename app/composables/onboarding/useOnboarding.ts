import type { Onboarding, OnboardingPatch, OnboardingStep } from '#shared/types/onboarding'

/**
 * Onboarding wizard state (GET / PATCH /onboarding). The server remembers every step, so the
 * wizard resumes where the admin left off — on any device.
 */
export function useOnboarding() {
  const api = useApi()
  const state = ref<Onboarding | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const error = shallowRef<ApiError | null>(null)
  const { handle } = useErrorHandler()

  async function load() {
    loading.value = true
    error.value = null
    try {
      state.value = (await api.get<Onboarding>('/onboarding')).data
    } catch (caught) {
      error.value = handle(caught, { silent: true })
    } finally {
      loading.value = false
    }
  }

  /** Save or skip one step; resolves true on success (field errors stay on `lastError`). */
  async function patch(body: OnboardingPatch): Promise<boolean> {
    if (saving.value) return false
    saving.value = true
    error.value = null
    try {
      state.value = (await api.patch<Onboarding>('/onboarding', body)).data
      return true
    } catch (caught) {
      error.value = handle(caught)
      return false
    } finally {
      saving.value = false
    }
  }

  const skip = (step: OnboardingStep) => patch({ step, action: 'skip' })

  async function finish(): Promise<boolean> {
    if (saving.value) return false
    saving.value = true
    try {
      state.value = (await api.post<Onboarding>('/onboarding/finish')).data
      return true
    } catch (caught) {
      handle(caught)
      return false
    } finally {
      saving.value = false
    }
  }

  return { state, loading, saving: readonly(saving), error: readonly(error), load, patch, skip, finish }
}
