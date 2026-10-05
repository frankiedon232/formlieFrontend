/** Response shapes from docs/API-CONTRACT.md (decrypted payloads). */

export interface ListMeta {
  page: number
  page_size: number
  total: number
  total_pages: number
  /** The count stopped at `total` (very large tables, F12 explorer): shown as "10,000+". */
  total_capped?: boolean
}

export interface CursorMeta {
  next_cursor: string | null
}

export interface ApiSuccess<TData = unknown, TMeta = Record<string, unknown>> {
  success: true
  data: TData
  meta: TMeta
}

export interface ApiErrorDetail {
  field: string
  message: string
}

export interface ApiErrorBody {
  code: string
  message: string
  trace_id: string
  details: ApiErrorDetail[]
}

export interface ApiFailure {
  success: false
  error: ApiErrorBody
}

export type ApiResponse<TData = unknown, TMeta = Record<string, unknown>> =
  ApiSuccess<TData, TMeta> | ApiFailure

export interface ListQuery {
  page?: number
  page_size?: number
  q?: string
  sort?: string
  from?: string
  to?: string
  [filter: `filter[${string}]`]: string | undefined
}

export interface CsrfTokenResponse {
  csrf_token: string
  expires_at: string
}

export interface HealthResponse {
  status: 'ok'
  mock: boolean
  time: string
}
