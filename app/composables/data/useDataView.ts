import type { LocationQuery, LocationQueryValue } from 'vue-router'
import type { ListMeta } from '#shared/types/api'

export interface DataFilterOption {
  label: string
  value: string
  /** Tailwind bg class for the square colour bullet (as in the sidebar). */
  dot?: string
}

export interface DataFilter {
  /** URL key (`?status=draft`) → API param `filter[key]`. */
  key: string
  label: string
  icon?: string
  options: DataFilterOption[]
  /** A heading the filter sits under in the Filter menu (e.g. "Questions"); filters without one come first. */
  group?: string
  /** The chip reads "Label: option" (when the option alone is unclear, e.g. a question's answer). */
  named?: boolean
}

export type DataViewMode = 'table' | 'grid'

export interface DataColumn {
  key: string
  label: string
  sortable?: boolean
  /** Hide below this breakpoint to keep phones readable. */
  hideBelow?: 'sm' | 'md' | 'lg'
  class?: string
  /** Hidden until someone ticks it in Columns (e.g. a form's other questions). */
  hidden?: boolean
  /** Always shown (can still be moved). */
  fixed?: boolean
}

export interface DataQuery {
  page: number
  pageSize: number
  q: string
  sort: string
  from: string
  to: string
  filters: Record<string, string[]>
}

export type DataFetcher<T> = (
  params: Record<string, string | number>,
  signal: AbortSignal,
) => Promise<{ data: T[]; meta: ListMeta }>

export interface UseDataViewOptions<T> {
  /** Unique per page; keys the remembered view mode. */
  id: string
  fetcher: DataFetcher<T>
  /** A getter keeps it live (filters whose options load later, e.g. folders or tags). */
  filters?: MaybeRefOrGetter<DataFilter[]>
  defaultSort?: string
  defaultPageSize?: number
  defaultView?: DataViewMode
}

export const PAGE_SIZES = [10, 20, 50, 100]

const first = (value: LocationQueryValue | LocationQueryValue[] | undefined): string =>
  (Array.isArray(value) ? value[0] : value) ?? ''

/**
 * State + loading for a server-side list (CLAUDE.md rule 6). The URL is the source of truth
 * (`?page=&page_size=&q=&sort=&from=&to=&status=…`), so views are shareable and back-button safe.
 * Stale requests are aborted; the table/grid choice is remembered per page.
 */
export function useDataView<T>(options: UseDataViewOptions<T>) {
  const route = useRoute()
  const router = useRouter()
  const { handle } = useErrorHandler()
  const path = route.path
  const defaultPageSize = options.defaultPageSize ?? 20
  const filterList = computed(() => toValue(options.filters) ?? [])
  const filterKeys = computed(() => filterList.value.map(filter => filter.key))

  const query = computed<DataQuery>(() => {
    const q = route.query
    const pageSize = Number(first(q.page_size))
    return {
      page: Math.max(1, Number(first(q.page)) || 1),
      pageSize: PAGE_SIZES.includes(pageSize) ? pageSize : defaultPageSize,
      q: first(q.q),
      sort: first(q.sort) || options.defaultSort || '',
      from: first(q.from),
      to: first(q.to),
      filters: Object.fromEntries(filterKeys.value.map(key => [key, first(q[key]).split(',').filter(Boolean)])),
    }
  })

  const hasActiveFilters = computed(
    () =>
      !!query.value.q ||
      !!query.value.from ||
      !!query.value.to ||
      Object.values(query.value.filters).some(values => values.length > 0),
  )

  /** Patch the URL; `null`/'' removes a key. Any change except paging returns to page 1. */
  function update(patch: Record<string, string | number | null>) {
    const merged: LocationQuery = { ...route.query }
    for (const [key, value] of Object.entries(patch)) merged[key] = value === null ? '' : String(value)
    const keepPage = 'page' in patch && merged.page !== '1'
    const next = Object.fromEntries(
      Object.entries(merged).filter(
        ([key, value]) => value !== '' && value != null && (key !== 'page' || keepPage),
      ),
    )
    return router.replace({ query: next })
  }

  const setPage = (page: number) => update({ page })
  const setPageSize = (size: number) => update({ page_size: size === defaultPageSize ? null : size })
  const setSearch = (q: string) => update({ q: q.trim() })
  const setSort = (sort: string) => update({ sort: sort === options.defaultSort ? null : sort })
  const setFilter = (key: string, values: string[]) => update({ [key]: values.join(',') })
  const setRange = (from: string, to: string) => update({ from, to })
  const reset = () =>
    update(Object.fromEntries(['q', 'from', 'to', 'sort', ...filterKeys.value].map(key => [key, null])))

  const view = useLocalStorage<DataViewMode>(`formalie:view:${options.id}`, options.defaultView ?? 'table')

  const rows = shallowRef<T[]>([])
  const meta = ref<ListMeta | null>(null)
  const loading = ref(false)
  const loaded = ref(false)
  const error = shallowRef<ApiError | null>(null)
  let controller: AbortController | null = null

  /** The list's search, sort, date range and filters as API params (no paging): the list and exports share them. */
  function params(): Record<string, string | number> {
    const { q, sort, from, to, filters } = query.value
    const out: Record<string, string | number> = {}
    if (q) out.q = q
    if (sort) out.sort = sort
    if (from) out.from = from
    if (to) out.to = to
    for (const [key, values] of Object.entries(filters)) if (values.length) out[`filter[${key}]`] = values.join(',')
    return out
  }

  async function load() {
    controller?.abort()
    const current = new AbortController()
    controller = current
    loading.value = true
    error.value = null
    try {
      const { page, pageSize } = query.value
      const result = await options.fetcher({ page, page_size: pageSize, ...params() }, current.signal)
      if (current !== controller) return
      rows.value = result.data
      meta.value = result.meta
      loaded.value = true
      // Page beyond the end (e.g. after a filter or deletion) → jump to the last page.
      if (result.meta.total > 0 && page > result.meta.total_pages) setPage(result.meta.total_pages)
    } catch (caught) {
      if (current !== controller) return
      const normalised = handle(caught, { silent: true })
      if (!normalised.aborted) error.value = normalised
    } finally {
      if (current === controller) loading.value = false
    }
  }

  // Only react while this page is shown (route.query changes before unmount on navigation).
  watch(
    () => (route.path === path ? JSON.stringify(query.value) : null),
    key => {
      if (key) load()
    },
    { immediate: true },
  )
  onScopeDispose(() => controller?.abort())

  return {
    query,
    hasActiveFilters,
    filters: filterList,
    view,
    rows,
    meta,
    loading,
    loaded,
    error,
    refresh: load,
    params,
    setPage,
    setPageSize,
    setSearch,
    setSort,
    setFilter,
    setRange,
    reset,
  }
}

export type DataViewState<T> = ReturnType<typeof useDataView<T>>
