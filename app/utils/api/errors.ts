import type { ApiErrorDetail } from '#shared/types/api'

/** Client-side codes (never sent by the server). Documented in docs/ERROR-CODES.md. */
export const NETWORK_ERROR = 'FRM-NET-1000'
export const ABORTED_ERROR = 'FRM-NET-1001'
export const BAD_RESPONSE_ERROR = 'FRM-NET-1002'

/** Every failed API call surfaces as this, with the server's FRM-* code and trace id. */
export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status = 0,
    public readonly traceId = '',
    public readonly details: ApiErrorDetail[] = [],
  ) {
    super(message)
    this.name = 'ApiError'
  }

  get aborted(): boolean {
    return this.code === ABORTED_ERROR
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}
