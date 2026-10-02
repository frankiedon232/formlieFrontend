interface RunOptions {
  /** Toast shown on success (already translated). */
  success?: string
  /** Don't toast errors (caller shows them inline); they are still returned. */
  silentError?: boolean
}

/**
 * Busy state + error handling for one action (CLAUDE.md rules 4, 5, 11):
 *
 *   const { busy, run } = useBusy()
 *   <UButton :loading="busy" @click="run(() => api.post('/forms', body), { success: t('…') })" />
 *
 * `run` ignores calls while busy (no double submit), always resets in `finally`,
 * and routes errors through useErrorHandler. Resolves to the result, or undefined on error.
 */
export function useBusy() {
  const busy = ref(false)
  const error = shallowRef<ApiError | null>(null)
  const { handle } = useErrorHandler()
  const toast = useToast()

  async function run<T>(action: () => Promise<T>, options: RunOptions = {}): Promise<T | undefined> {
    if (busy.value) return undefined
    busy.value = true
    error.value = null
    try {
      const result = await action()
      if (options.success)
        toast.add({ title: options.success, color: 'success', icon: 'i-lucide-circle-check' })
      return result
    } catch (caught) {
      error.value = handle(caught, { silent: options.silentError })
      return undefined
    } finally {
      busy.value = false
    }
  }

  return { busy: readonly(busy), error: readonly(error), run }
}
