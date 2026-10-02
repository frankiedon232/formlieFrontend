import type { FormError } from '@nuxt/ui'

interface HandleOptions {
  /** No toast (e.g. the form shows inline errors). The normalised error is still returned. */
  silent?: boolean
  /** Toast title override (i18n already applied). */
  title?: string
}

/**
 * Maps any thrown value to a friendly, translated toast (CLAUDE.md rule 4).
 * `errors.<FRM code>` messages live in every locale; unknown codes fall back to the server's
 * English message, then to FRM-GEN-5000. The trace id is shown so support can find the logs.
 */
export function useErrorHandler() {
  const { t, te } = useI18n()
  const toast = useToast()
  const { copy } = useClipboard({ legacy: true })

  function normalise(error: unknown): ApiError {
    if (isApiError(error)) return error
    if (import.meta.dev) console.error('[unhandled]', error)
    return new ApiError('FRM-GEN-5000', 'Something went wrong.')
  }

  function messageFor(error: ApiError): string {
    const key = `errors.${error.code}`
    if (te(key)) return t(key)
    return error.message || t('errors.FRM-GEN-5000')
  }

  function handle(error: unknown, options: HandleOptions = {}): ApiError {
    const normalised = normalise(error)
    if (normalised.aborted || options.silent) return normalised

    toast.add({
      id: normalised.traceId || undefined,
      title: options.title ?? messageFor(normalised),
      description: normalised.traceId ? t('errorUi.reference', { id: normalised.traceId }) : undefined,
      color: 'error',
      icon: 'i-lucide-circle-alert',
      actions: normalised.traceId
        ? [
            {
              label: t('errorUi.copy'),
              icon: 'i-lucide-copy',
              color: 'neutral',
              variant: 'outline',
              onClick: () => {
                copy(normalised.traceId)
                toast.add({ title: t('errorUi.copied'), color: 'success', icon: 'i-lucide-check' })
              },
            },
          ]
        : undefined,
    })
    return normalised
  }

  /** Server field errors (FRM-GEN-1002 details) → UForm `setErrors()` shape. */
  function fieldErrors(error: unknown): FormError[] {
    const normalised = normalise(error)
    return normalised.details.map(detail => ({ name: detail.field, message: detail.message }))
  }

  return { handle, fieldErrors, messageFor, normalise }
}
