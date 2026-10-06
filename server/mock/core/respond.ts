import type { ApiErrorDetail, ApiResponse, ListMeta } from '#shared/types/api'
import { ERROR_CODES, type ErrorCode } from '#shared/utils/errors/codes'

/** What a mock route returns; the envelope wrapper turns it into the HTTP reply. */
export interface MockReply {
  status: number
  body: ApiResponse
}

export class MockError extends Error {
  constructor(
    public readonly code: ErrorCode,
    public readonly details: ApiErrorDetail[] = [],
  ) {
    super(code)
  }
}

export function ok<T>(data: T, meta: object = {}, status = 200): MockReply {
  return { status, body: { success: true, data, meta: meta as Record<string, unknown> } }
}

export function fail(code: ErrorCode, details: ApiErrorDetail[] = []): MockReply {
  const definition = ERROR_CODES[code]
  return {
    status: definition.status,
    body: {
      success: false,
      error: { code, message: definition.message, trace_id: crypto.randomUUID(), details },
    },
  }
}

const MAX_PAGE_SIZE = 100

/**
 * Server-side pagination, search and sort exactly as API-CONTRACT.md describes:
 * `page`, `page_size` (≤100), `q`, `sort` (`-updated_at` = descending).
 */
export function paginate<T extends object>(
  items: T[],
  query: Record<string, unknown>,
  search?: (item: T, q: string) => boolean,
): { data: T[]; meta: ListMeta } {
  const page = Math.max(1, Number(query.page) || 1)
  const pageSize = Math.min(MAX_PAGE_SIZE, Math.max(1, Number(query.page_size) || 20))
  const q = typeof query.q === 'string' ? query.q.trim().toLowerCase() : ''

  let result = q && search ? items.filter(item => search(item, q)) : [...items]

  if (typeof query.sort === 'string' && query.sort) {
    const descending = query.sort.startsWith('-')
    const key = (descending ? query.sort.slice(1) : query.sort) as keyof T
    result.sort((a, b) => {
      const av = a[key]
      const bv = b[key]
      if (av === bv) return 0
      const order = String(av ?? '').localeCompare(String(bv ?? ''), undefined, { numeric: true })
      return descending ? -order : order
    })
  }

  const total = result.length
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  result = result.slice((page - 1) * pageSize, page * pageSize)

  return { data: result, meta: { page, page_size: pageSize, total, total_pages: totalPages } }
}

/**
 * List filters from the query: `filter[key]=a,b` arrives as flat keys (the portal's query is not
 * nested); a nested `filter` object is accepted too.
 */
export function filtersOf(query: Record<string, unknown>): Record<string, string | undefined> {
  const out: Record<string, string | undefined> = {}
  const nested = query.filter
  if (nested && typeof nested === 'object') for (const [key, value] of Object.entries(nested)) if (typeof value === 'string') out[key] = value
  for (const [key, value] of Object.entries(query)) {
    const match = /^filter\[(.+)\]$/.exec(key)
    if (match && typeof value === 'string') out[match[1]!] = value
  }
  return out
}
