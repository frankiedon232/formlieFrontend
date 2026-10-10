<!--
  List Option (F15 M1; locked list format, rule 21): every reusable choice list of the workspace. Two
  chart cards (options in all lists; by state, legend filters), then table / cards with search, state
  filter and sort. A row or card opens the list's editor; ⋯ / right-click: open, duplicate, delete
  (forms keep their copies; asks first, says how many forms use it). New list (N).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { OptionList, OptionListInsights, OptionListRow } from '#shared/types/forms'

definePageMeta({ breadcrumb: 'nav.optionSets' })
const { t } = useI18n()
const { listName, listDescription, levelLabel } = useBuiltInNames()
useHead({ title: () => t('nav.optionSets') })
const api = useApi()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const { handle } = useErrorHandler()
const { relative, dateTime, number } = useFormat()

const view = useTemplateRef<{ refresh: () => Promise<void> }>('view')
const insights = ref<OptionListInsights | null>(null)
async function loadInsights() {
  try {
    insights.value = (await api.get<OptionListInsights>('/option-lists/insights', undefined, { background: !!insights.value })).data
  } catch {
    insights.value ??= null
  }
}
onMounted(loadInsights)
const refreshAll = () => Promise.all([view.value?.refresh(), loadInsights()])

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('optionSets.col.name'), sortable: true, fixed: true },
  { key: 'items_count', label: t('optionSets.col.items'), sortable: true },
  { key: 'forms_count', label: t('optionSets.col.forms'), sortable: true, hideBelow: 'sm' },
  { key: 'languages', label: t('optionSets.col.languages'), hideBelow: 'md' },
  { key: 'updated_at', label: t('optionSets.col.updated'), sortable: true, hideBelow: 'lg' },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'status', label: t('optionSets.col.state'), icon: 'i-lucide-circle-dot', options: [{ value: 'in_use', label: t('optionSets.state.in_use'), dot: 'bg-green-500' }, { value: 'unused', label: t('optionSets.state.unused'), dot: 'bg-amber-500' }, { value: 'retired', label: t('optionSets.state.retired'), dot: 'bg-(--ui-border-accented)' }] },
])
const sortOptions = computed(() => [
  { label: t('forms.sortName'), value: 'name' },
  { label: t('optionSets.sort.items'), value: '-items_count' },
  { label: t('optionSets.sort.forms'), value: '-forms_count' },
  { label: t('optionSets.sort.updated'), value: '-updated_at' },
])
const fetcher: DataFetcher<OptionListRow> = (params, signal) => api.list<OptionListRow>('/option-lists', params, { signal })
const statusFilter = computed(() => (typeof route.query.status === 'string' && !route.query.status.includes(',') ? route.query.status : null))
const pickStatus = (status: string) => void router.replace({ query: { ...route.query, status: statusFilter.value === status ? undefined : status, page: undefined } })

const open = (row: OptionList) => navigateTo(`/option-sets/${row.id}`)
const newOpen = ref(false)
// What this person may do (F22 R2 M3): create, duplicate; each list says whether it may change or go
const { can } = useCan()
defineShortcuts({ n: { usingInput: false, handler: () => can('lists.create') && (newOpen.value = true) } })
const created = (list: OptionList) => navigateTo(`/option-sets/${list.id}`)

const busy = ref<string | null>(null)
async function act(row: OptionListRow, work: () => Promise<unknown>, message: string) {
  if (busy.value) return
  busy.value = row.id
  try {
    await work()
    toast.add({ title: message, color: 'success', icon: 'i-lucide-circle-check' })
    await refreshAll()
  } catch (error) {
    handle(error)
  } finally {
    busy.value = null
  }
}
async function remove(row: OptionListRow) {
  const ok = await confirm({ title: t('optionSets.deleteTitle', { name: row.name }), description: row.forms_count ? t('optionSets.deleteUsed', { n: row.forms_count }, row.forms_count) : t('optionSets.deleteDesc'), confirmLabel: t('apiService.delete.confirm'), danger: true })
  if (ok) await act(row, () => api.del(`/option-lists/${row.id}`), t('optionSets.deleted', { name: row.name }))
}
const rowActions = (row: OptionListRow): DropdownMenuItem[][] =>
  [
    [
      { label: t('apiService.actions.open'), icon: 'i-lucide-panel-right-open', onSelect: () => void open(row) },
      ...(can('lists.duplicate') ? [{ label: t('optionSets.duplicate'), icon: 'i-lucide-copy', onSelect: () => void act(row, () => api.post(`/option-lists/${row.id}/duplicate`), t('optionSets.duplicated', { name: row.name })) }] : []),
    ],
    row.can?.delete ? [{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove(row) }] : [],
  ].filter(group => group.length)
</script>

<template>
  <AppPanel id="option-sets" :title="t('nav.optionSets')" :subtitle="t('optionSets.subtitle')">
    <template v-if="can('lists.create')" #actions>
      <UButton :label="t('optionSets.new')" icon="i-lucide-plus" color="neutral" @click="newOpen = true">
        <template #trailing><UKbd value="N" size="sm" class="hidden sm:inline-flex" /></template>
      </UButton>
    </template>

    <OptionSetsOverview :insights="insights" :selected="statusFilter" @pick="pickStatus" />

    <DataView
      id="option-sets"
      ref="view"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="name"
      default-view="grid"
      :row-actions="rowActions"
      :busy="row => busy === row.id"
      :open-row="open"
      :search-placeholder="t('optionSets.search')"
      empty-icon="i-lucide-list-checks"
      :empty-title="t('optionSets.empty')"
      :empty-description="t('optionSets.emptyDesc')"
    >
      <template #name-cell="{ row }">
        <div class="flex min-w-0 flex-col">
          <span class="flex min-w-0 items-center gap-1.5">
            <UIcon v-if="row.original.retired_count" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('optionSets.hasRetired')" />
            <span class="truncate font-medium text-highlighted">{{ listName(row.original) }}</span>
          </span>
          <span v-if="row.original.description" class="max-w-80 truncate text-xs text-muted">{{ listDescription(row.original) }}</span>
          <span v-if="row.original.levels" class="flex max-w-80 items-center gap-1 text-xs text-default"><UIcon name="i-lucide-network" class="size-3 shrink-0 text-muted" /><span class="truncate">{{ row.original.levels.map((level: { key: string; label: string }) => levelLabel(row.original, level)).join(' → ') }}</span></span>
        </div>
      </template>
      <template #items_count-cell="{ row }"><span class="text-muted tabular-nums">{{ t('optionSets.itemsCount', { n: number(row.original.items_count) }, row.original.items_count) }}<template v-if="row.original.retired_count"> · {{ t('optionSets.retiredCount', { n: row.original.retired_count }, row.original.retired_count) }}</template></span></template>
      <template #forms_count-cell="{ row }"><span class="text-muted tabular-nums">{{ t('optionSets.formsCount', { n: number(row.original.forms_count) }, row.original.forms_count) }}</span></template>
      <template #languages-cell="{ row }"><span class="text-xs text-muted">{{ row.original.languages.length ? row.original.languages.map((code: string) => code.toUpperCase()).join(' · ') : '–' }}</span></template>
      <template #updated_at-cell="{ row }"><UTooltip :text="dateTime(row.original.updated_at)"><span class="whitespace-nowrap text-muted">{{ relative(row.original.updated_at) }}</span></UTooltip></template>
      <template v-if="can('lists.create')" #empty-actions><UButton :label="t('optionSets.new')" icon="i-lucide-plus" color="neutral" @click="newOpen = true" /></template>
      <template #grid-card="{ row }"><OptionSetsCard :item="row" :actions="rowActions(row)" :busy="busy === row.id" /></template>
    </DataView>

    <FormsBuilderListModal v-model:open="newOpen" :list="null" @saved="created" />
  </AppPanel>
</template>
