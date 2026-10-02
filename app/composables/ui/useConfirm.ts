export interface ConfirmOptions {
  title: string
  description?: string
  confirmLabel?: string
  cancelLabel?: string
  /** Red confirm button for destructive actions. */
  danger?: boolean
}

interface PendingConfirm extends ConfirmOptions {
  resolve: (confirmed: boolean) => void
}

/** The single <AppConfirmDialog> in the layout renders whatever is pending here. */
const pending = shallowRef<PendingConfirm | null>(null)

/**
 * Promise-based confirmation (CLAUDE.md rule 13):
 *
 *   const confirm = useConfirm()
 *   if (await confirm({ title: t('…'), danger: true })) await remove()
 */
export function useConfirm() {
  return (options: ConfirmOptions): Promise<boolean> =>
    new Promise(resolve => {
      pending.value?.resolve(false)
      pending.value = { ...options, resolve }
    })
}

/** Used by AppConfirmDialog only. */
export function useConfirmState() {
  function settle(confirmed: boolean) {
    pending.value?.resolve(confirmed)
    pending.value = null
  }
  return { pending: readonly(pending), settle }
}
