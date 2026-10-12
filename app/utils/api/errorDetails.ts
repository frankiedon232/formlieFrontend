import type { ApiErrorDetail } from '#shared/types/api'

/**
 * Errors whose meaning is in their details (B16): the same code answers for different reasons, so the
 * message key is picked by `field` + `message`. useErrorHandler() uses the key when it is translated,
 * else the code's own message. Keys live under `errors.detail.*` in every locale.
 */
const DETAIL_KEYS: Record<string, Record<string, string>> = {
  'FRM-PERM-1001': {
    'support:read_only': 'errors.detail.supportReadOnly',
    'support:not_in_support_sessions': 'errors.detail.notInSupportSessions',
    'workspace:read_only': 'errors.detail.workspaceReadOnly',
    'workspace:closing': 'errors.detail.workspaceClosing',
  },
}

export function errorDetailKey(code: string, details: readonly ApiErrorDetail[] | null | undefined): string | null {
  const known = DETAIL_KEYS[code]
  if (!known || !details?.length) return null
  for (const detail of details) {
    const key = known[`${detail.field ?? ''}:${detail.message ?? ''}`]
    if (key) return key
  }
  return null
}
