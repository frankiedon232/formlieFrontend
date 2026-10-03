<!--
  Audit trail (PROGRESS.md F4): every action — who, what, when, where, before / after.
  DataView list (table / grid, filters, date range, server paging) · `?event=<id>` opens the detail
  slide-over (shareable) · export with progress. Workspace owners / admins only until F21.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { AuditEvent, AuditFacets, AuditOutcome } from '#shared/types/audit'
import { AUDIT_AREAS } from '#shared/utils/audit/events'

definePageMeta({ breadcrumb: 'nav.audit' })

const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const session = useSession()
const toast = useToast()
const { copy } = useClipboard({ legacy: true })
const { relative, dateTime } = useFormat()
const format = useAuditFormat()
const { endSide } = useAppLocale()
const { handle } = useErrorHandler()
useHead({ title: () => t('nav.audit') })

const canView = computed(() => session.user.value?.role !== 'member')

const facets = ref<AuditFacets>({ actors: [], countries: [] })
onMounted(async () => {
  if (!canView.value) return
  try {
    facets.value = (await api.get<AuditFacets>('/audit-logs/facets')).data
  } catch {
    // The person / country filters simply stay empty; the list reports its own errors.
  }
})

const OUTCOMES: AuditOutcome[] = ['success', 'failure', 'blocked']

const filters = computed<DataFilter[]>(() => [
  {
    key: 'area',
    label: t('audit.filter.area'),
    options: AUDIT_AREAS.map(area => ({ value: area, label: format.areaLabel(area) })),
  },
  {
    key: 'outcome',
    label: t('audit.filter.outcome'),
    options: OUTCOMES.map(value => ({ value, label: format.outcomeLabel(value), dot: OUTCOME_DOTS[value] })),
  },
  {
    key: 'actor_id',
    label: t('audit.filter.person'),
    options: facets.value.actors.map(actor => ({ value: actor.id, label: actor.name })),
  },
  {
    key: 'country',
    label: t('audit.filter.country'),
    options: facets.value.countries.map(code => ({ value: code, label: format.countryName(code) })),
  },
])

const columns = computed<DataColumn[]>(() => [
  { key: 'occurred_at', label: t('audit.col.when'), sortable: true },
  { key: 'actor', label: t('audit.col.person'), hideBelow: 'sm' },
  { key: 'action', label: t('audit.col.action') },
  { key: 'outcome', label: t('audit.col.result'), hideBelow: 'sm' },
  { key: 'location', label: t('audit.col.location'), hideBelow: 'md' },
  { key: 'device', label: t('audit.col.device'), hideBelow: 'lg' },
])

const sortOptions = computed(() => [
  { label: t('audit.sortNewest'), value: '-occurred_at' },
  { label: t('audit.sortOldest'), value: 'occurred_at' },
])

const fetcher: DataFetcher<AuditEvent> = (params, signal) =>
  api.list<AuditEvent>('/audit-logs', params, { signal })

// ── Detail slide-over, driven by ?event=<id> so a link opens the same event ──────────
const selected = shallowRef<AuditEvent | null>(null)
const detailOpen = computed({
  get: () => !!route.query.event,
  set: value => {
    if (!value) closeEvent()
  },
})

function openEvent(event: AuditEvent) {
  selected.value = event
  router.replace({ query: { ...route.query, event: event.id } })
}
function closeEvent() {
  const { event: _event, ...rest } = route.query
  router.replace({ query: rest })
}

const loadingEvent = ref(false)
watch(
  () => route.query.event,
  async id => {
    if (typeof id !== 'string' || !id || !canView.value || selected.value?.id === id) return
    loadingEvent.value = true
    try {
      selected.value = (await api.get<AuditEvent>(`/audit-logs/${id}`)).data
    } catch (error) {
      handle(error)
      closeEvent()
    } finally {
      loadingEvent.value = false
    }
  },
  { immediate: true },
)

/** "Show all" in the detail: apply a filter / search to the list and close the panel. */
function applyFilter(patch: Record<string, string>) {
  const { event: _event, page: _page, ...rest } = route.query
  router.replace({ query: { ...rest, ...patch } })
}

function rowActions(event: AuditEvent): DropdownMenuItem[][] {
  return [
    [
      {
        label: t('audit.detail.viewDetails'),
        icon: 'i-lucide-panel-right-open',
        onSelect: () => openEvent(event),
      },
      ...(event.actor.id
        ? [
            {
              label: t('audit.detail.byPerson'),
              icon: 'i-lucide-user-search',
              onSelect: () => applyFilter({ actor_id: event.actor.id! }),
            },
          ]
        : []),
    ],
    [
      {
        label: t('audit.detail.copyRequestId'),
        icon: 'i-lucide-copy',
        onSelect: () => {
          copy(event.request_id)
          toast.add({ title: t('audit.detail.copied'), color: 'success', icon: 'i-lucide-check' })
        },
      },
    ],
  ]
}

// ── Export: the list's current search, filters and dates go with it ──────────────────
const exportOpen = ref(false)
const exportFilters = computed(() => {
  const params: Record<string, string> = {}
  const query = route.query
  for (const key of ['q', 'from', 'to'])
    if (typeof query[key] === 'string' && query[key]) params[key] = query[key] as string
  for (const filter of filters.value)
    if (typeof query[filter.key] === 'string' && query[filter.key])
      params[`filter[${filter.key}]`] = query[filter.key] as string
  return params
})

const SECURITY_QUERY = { area: 'auth', outcome: 'failure,blocked' }
const securityActive = computed(
  () => route.query.area === SECURITY_QUERY.area && route.query.outcome === SECURITY_QUERY.outcome,
)

defineShortcuts({ e: () => canView.value && (exportOpen.value = true) })
</script>

<template>
  <AppPanel
    id="audit"
    :title="t('nav.audit')"
    :subtitle="t('audit.description')"
    subtitle-icon="i-lucide-shield-check"
  >
    <template v-if="canView" #actions>
      <UButton
        icon="i-lucide-shield-alert"
        :label="t('audit.security')"
        color="neutral"
        :variant="securityActive ? 'soft' : 'outline'"
        :to="{ path: '/audit', query: securityActive ? {} : SECURITY_QUERY }"
        :aria-pressed="securityActive"
      />
      <UButton
        icon="i-lucide-download"
        :label="t('audit.export.button')"
        color="neutral"
        @click="exportOpen = true"
      >
        <template #trailing>
          <UKbd value="E" class="hidden lg:inline-flex" />
        </template>
      </UButton>
    </template>

    <UEmpty
      v-if="!canView"
      icon="i-lucide-lock"
      :title="t('audit.noAccessTitle')"
      :description="t('audit.noAccessDesc')"
      variant="outline"
    />

    <DataView
      v-else
      id="audit"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="-occurred_at"
      date-range
      :row-actions="rowActions"
      :search-placeholder="t('audit.searchPlaceholder')"
      empty-icon="i-lucide-scroll-text"
      :empty-title="t('audit.emptyTitle')"
      :empty-description="t('audit.emptyDesc')"
    >
      <template #occurred_at-cell="{ row }">
        <UTooltip :text="dateTime(row.original.occurred_at)">
          <span class="whitespace-nowrap">{{ relative(row.original.occurred_at) }}</span>
        </UTooltip>
      </template>
      <template #actor-cell="{ row }">
        <UUser
          :name="row.original.actor.name"
          :description="format.actorDescription(row.original)"
          :avatar="{
            alt: row.original.actor.name,
            icon: row.original.actor.id ? undefined : 'i-lucide-user-x',
          }"
          size="sm"
          :ui="{ name: 'truncate max-w-48', description: 'truncate max-w-48' }"
        />
      </template>
      <template #action-cell="{ row }">
        <UButton
          color="neutral"
          variant="ghost"
          class="-mx-2 max-w-72 gap-2.5 text-start"
          @click="openEvent(row.original)"
        >
          <UIcon :name="format.actionIcon(row.original.action)" class="size-4 shrink-0 text-muted" />
          <span class="min-w-0">
            <span class="block truncate font-medium text-highlighted">{{
              format.actionLabel(row.original.action)
            }}</span>
            <span class="block truncate text-xs font-normal text-muted">
              <span class="sm:hidden">{{ row.original.actor.name }} · </span>
              {{ row.original.resource?.name ?? format.areaLabel(row.original.area) }}
            </span>
          </span>
        </UButton>
      </template>
      <template #outcome-cell="{ row }">
        <UBadge
          :label="format.outcomeLabel(row.original.outcome)"
          :color="format.outcomeColor(row.original.outcome)"
          variant="subtle"
          size="sm"
          class="rounded-md"
        />
      </template>
      <template #location-cell="{ row }">
        <div class="flex min-w-0 items-center gap-2">
          <UIcon
            :name="
              row.original.location.country
                ? format.countryFlag(row.original.location.country)
                : 'i-lucide-map-pin-off'
            "
            class="size-4 shrink-0 text-muted"
          />
          <div class="min-w-0">
            <p class="truncate">{{ format.place(row.original) }}</p>
            <p class="truncate font-mono text-xs text-muted">{{ row.original.location.ip }}</p>
          </div>
        </div>
      </template>
      <template #device-cell="{ row }">
        <span class="flex items-center gap-2 whitespace-nowrap">
          <UIcon :name="format.deviceIcon(row.original.device)" class="size-4 text-muted" />
          {{ format.deviceLabel(row.original.device) }}
        </span>
      </template>

      <template #grid-card="{ row }">
        <AuditEventCard :event="row" :actions="rowActions(row)" @open="openEvent" />
      </template>
    </DataView>

    <USlideover
      v-model:open="detailOpen"
      :side="endSide"
      :title="selected ? format.actionLabel(selected.action) : t('common.loading')"
      :description="selected ? `${selected.actor.name} · ${relative(selected.occurred_at)}` : undefined"
      :ui="{ content: 'w-full sm:max-w-xl' }"
    >
      <template #body>
        <div v-if="loadingEvent || !selected" class="space-y-4" :aria-label="t('common.loading')">
          <USkeleton class="h-6 w-40" />
          <USkeleton class="h-24 w-full" />
          <USkeleton class="h-32 w-full" />
        </div>
        <AuditEventDetail v-else :event="selected" @open="openEvent" @filter="applyFilter" />
      </template>
    </USlideover>

    <AuditExportModal
      v-model:open="exportOpen"
      :filters="exportFilters"
      :filter-count="Object.keys(exportFilters).length"
    />
  </AppPanel>
</template>
