<!--
  AI assistant → History (F19 M1; locked list format, rule 21): every request, yours or (for people who
  manage the assistant) the workspace's. Two chart cards (credits this month; requests by kind, the legend
  filters), then DataView (table / card) with kind, status and person filters, date range, search and sort.
  A row opens the panel (what was asked, what came back, what it read); ⋯: open what it made, delete.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import { AI_KINDS, AI_STATUSES, type AiRequestInsights, type AiRequestRow, type AiUsage } from '#shared/types/ai'
import type { Directory } from '#shared/types/directory'
import { AI_KIND_META } from '#shared/utils/ai/kinds'

definePageMeta({ breadcrumb: 'nav.aiHistory' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const { handle } = useErrorHandler()
const { relative, dateTime, number } = useFormat()
const { can } = useCan()
const ai = useAi()
const { titleOf } = useAiText()
useHead({ title: () => t('nav.aiHistory') })

const view = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: Ref<AiRequestRow[]> } }>('view')
const usage = ref<AiUsage | null>(null)
const insights = ref<AiRequestInsights | null>(null)
const people = ref<{ id: string; name: string }[]>([])
async function loadCards() {
  try {
    const [u, i] = await Promise.all([api.get<AiUsage>('/ai/usage'), api.get<AiRequestInsights>('/ai/requests/insights')])
    usage.value = u.data
    insights.value = i.data
  } catch (error) {
    handle(error, { silent: true })
  }
}
onMounted(async () => {
  void ai.load()
  void loadCards()
  if (!can('ai.settings')) return
  try {
    people.value = (await api.get<Directory>('/directory', undefined, { background: true })).data.users
  } catch {
    people.value = []
  }
})
const refreshAll = () => Promise.all([view.value?.refresh(), loadCards()])

const columns = computed<DataColumn[]>(() => [
  { key: 'title', label: t('ai.history.col.request'), sortable: true, fixed: true },
  { key: 'kind', label: t('ai.history.col.kind'), hideBelow: 'sm' },
  { key: 'status', label: t('ai.history.col.status') },
  { key: 'by', label: t('ai.history.col.by'), hideBelow: 'md' },
  { key: 'credits', label: t('ai.history.col.credits'), sortable: true, hideBelow: 'lg' },
  { key: 'created_at', label: t('ai.history.col.when'), sortable: true, hideBelow: 'sm' },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'kind', label: t('ai.history.col.kind'), icon: 'i-lucide-shapes', options: AI_KINDS.map(kind => ({ value: kind, label: t(`ai.kind.${kind}`), icon: AI_KIND_META[kind].icon })) },
  { key: 'status', label: t('ai.history.col.status'), icon: 'i-lucide-circle-dot', options: AI_STATUSES.map(status => ({ value: status, label: t(`status.${status}`) })) },
  ...(people.value.length ? [{ key: 'person', label: t('ai.history.col.by'), icon: 'i-lucide-user', options: people.value.map(person => ({ value: person.id, label: person.name })) }] : []),
])
const sortOptions = computed(() => [
  { label: t('ai.history.sortNewest'), value: '-created_at' },
  { label: t('ai.history.sortOldest'), value: 'created_at' },
  { label: t('ai.history.sortCredits'), value: '-credits' },
  { label: t('ai.history.sortTitle'), value: 'title' },
])
const fetcher: DataFetcher<AiRequestRow> = (params, signal) => api.list<AiRequestRow>('/ai/requests', params, { signal })

const kindFilter = computed(() => (typeof route.query.kind === 'string' && !route.query.kind.includes(',') ? route.query.kind : null))
const filterKind = (kind: string) => void router.replace({ query: { ...route.query, kind: kindFilter.value === kind ? undefined : kind, page: undefined } })

// Panel with K / J through the rows on the page
const panelOpen = ref(false)
const openId = ref<string | null>(null)
const ids = ref<string[]>([])
function openRow(row: AiRequestRow) {
  ids.value = (view.value?.state.rows.value ?? []).map(item => item.id)
  openId.value = row.id
  panelOpen.value = true
}

const deleting = ref<string | null>(null)
async function remove(row: Pick<AiRequestRow, 'id' | 'title' | 'title_key'>) {
  if (!(await useConfirm()({ title: t('ai.history.deleteTitle', { name: titleOf(row) }), description: t('ai.history.deleteDesc'), confirmLabel: t('ai.history.delete'), danger: true }))) return
  deleting.value = row.id
  try {
    await api.del(`/ai/requests/${row.id}`)
    toast.add({ title: t('ai.history.deleted'), color: 'success', icon: 'i-lucide-circle-check' })
    if (openId.value === row.id) panelOpen.value = false
    await refreshAll()
  } catch (error) {
    handle(error)
  } finally {
    deleting.value = null
  }
}
const targetLink = (row: Pick<AiRequestRow, 'target'>) =>
  row.target?.type === 'form' ? `/forms/${row.target.id}` : row.target?.type === 'template' ? '/templates' : row.target?.type === 'theme' ? '/settings/themes' : null
const rowActions = (row: Pick<AiRequestRow, 'id' | 'title' | 'title_key' | 'target' | 'kind' | 'mine'>): DropdownMenuItem[][] => [
  [
    ...(targetLink(row) ? [{ label: t('ai.history.openTarget'), icon: 'i-lucide-external-link', to: targetLink(row)! }] : []),
    ...(can(AI_KIND_META[row.kind].permission) ? [{ label: t('ai.history.again'), icon: AI_KIND_META[row.kind].icon, to: AI_KIND_META[row.kind].page }] : []),
  ],
  ...(row.mine || can('ai.settings') ? [[{ label: t('ai.history.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove(row) }]] : []),
]
</script>

<template>
  <AppPanel id="ai-history" :title="t('nav.aiHistory')" :subtitle="can('ai.settings') ? t('ai.history.subtitleAll') : t('ai.history.subtitleMine')" subtitle-icon="i-lucide-history">
    <AiOff v-if="!ai.enabled.value && !insights?.total" />
    <template v-else>
      <AiOverviewCards :usage="usage" :by-kind="insights?.by_kind ?? null" :kind="kindFilter" :kinds-title="t('ai.history.byKind')" :kinds-note="insights ? t('ai.history.people', { n: number(insights.people) }, insights.people) : undefined" @kind="filterKind" />

      <DataView
      id="ai-history"
        ref="view"
        empty-help="ai-overview"
        :columns="columns"
        :fetcher="fetcher"
        :filters="filters"
        :sort-options="sortOptions"
        default-sort="-created_at"
        date-range
        :row-actions="rowActions"
        :busy="row => deleting === row.id"
        :open-row="openRow"
        :search-placeholder="t('ai.history.search')"
        empty-icon="i-lucide-sparkles"
        :empty-title="t('ai.history.emptyTitle')"
        :empty-description="t('ai.history.emptyDesc')"
      >
        <template #title-cell="{ row }">
          <div class="flex min-w-0 flex-col">
            <span class="flex min-w-0 items-center gap-1.5">
              <UIcon v-if="row.original.status === 'failed'" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('status.failed')" />
              <span class="truncate font-medium text-highlighted">{{ titleOf(row.original) }}</span>
            </span>
            <span class="truncate text-xs text-muted">{{ row.original.target?.name || t(`ai.kindHint.${row.original.kind}`) }}</span>
          </div>
        </template>
        <template #kind-cell="{ row }">
          <UBadge :label="t(`ai.kind.${row.original.kind}`)" :icon="AI_KIND_META[row.original.kind as AiRequestRow['kind']].icon" color="neutral" variant="outline" size="sm" class="rounded-md" />
        </template>
        <template #status-cell="{ row }">
          <DataStatusBadge :status="row.original.status" />
        </template>
        <template #by-cell="{ row }">
          <span class="flex min-w-0 items-center gap-2">
            <UAvatar :alt="row.original.by.name" size="2xs" />
            <span class="truncate">{{ row.original.mine ? t('ai.history.you') : row.original.by.name }}</span>
          </span>
        </template>
        <template #credits-cell="{ row }">
          <span class="tabular-nums">{{ number(row.original.credits) }}</span>
        </template>
        <template #created_at-cell="{ row }">
          <UTooltip :text="dateTime(row.original.created_at)">
            <span class="whitespace-nowrap text-muted">{{ relative(row.original.created_at) }}</span>
          </UTooltip>
        </template>
        <template #empty-actions>
          <UButton v-if="can('ai.create')" :label="t('nav.aiCreateForm')" icon="i-lucide-file-plus-2" color="neutral" to="/ai/create-form" />
        </template>
        <template #grid-card="{ row }">
          <AiRequestCard :item="row" :actions="rowActions(row)" :limit="usage?.limit ?? 0" />
        </template>
      </DataView>

      <AiRequestDetail :id="openId" v-model:open="panelOpen" :ids="ids.length ? ids : openId ? [openId] : []" :actions="rowActions" @go="id => (openId = id)" />
    </template>
  </AppPanel>
</template>
