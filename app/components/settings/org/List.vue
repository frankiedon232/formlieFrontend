<!--
  An organisation list page (F14 M2; locked list format, rule 21), the same for every kind: two chart
  cards (people, by state; the legend filters), then DataView (table / cards) with state filter,
  search, sort and selection (Merge the selected). A row or card opens its panel (`?item=`); ⋯ /
  right-click: open, edit, merge into another, archive / restore, delete. Header: Import and New (N).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { OrgImportResult, OrgInsights, OrgItem, OrgKind } from '#shared/types/org'

const props = defineProps<{ kind: OrgKind; plain?: boolean }>()
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const { relative, dateTime, number } = useFormat()

const view = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: Ref<OrgItem[]> } }>('view')
const panel = useTemplateRef<{ reload: () => void }>('panel')
const insights = ref<OrgInsights | null>(null)
async function loadInsights() {
  try {
    insights.value = (await api.get<OrgInsights>(`/org/${props.kind}/insights`, undefined, { background: !!insights.value })).data
  } catch {
    insights.value ??= null
  }
}
watch(() => props.kind, () => ((insights.value = null), void loadInsights()), { immediate: true })
const refreshAll = () => Promise.all([view.value?.refresh(), loadInsights(), panel.value?.reload()])
const actions = useOrgActions(() => props.kind, refreshAll)

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('settings.org.col.name'), sortable: true, fixed: true },
  { key: 'status', label: t('settings.org.col.state'), hideBelow: 'sm' },
  { key: 'members', label: t('settings.org.col.people'), sortable: true },
  { key: 'forms_count', label: t('settings.org.col.forms'), hideBelow: 'md' },
  { key: 'updated_at', label: t('settings.org.col.updated'), sortable: true, hideBelow: 'lg' },
  { key: 'created_at', label: t('settings.org.col.created'), sortable: true, hideBelow: 'lg', hidden: true },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'status', label: t('settings.org.col.state'), icon: 'i-lucide-circle-dot', options: [{ value: 'in_use', label: t('settings.org.inUse'), dot: 'bg-green-500' }, { value: 'empty', label: t('settings.org.empty'), dot: 'bg-amber-500' }, { value: 'archived', label: t('settings.org.archived'), dot: 'bg-(--ui-border-accented)' }] },
])
const sortOptions = computed(() => [
  { label: t('forms.sortName'), value: 'name' },
  { label: t('settings.org.sort.people'), value: '-members' },
  { label: t('settings.org.sort.updated'), value: '-updated_at' },
  { label: t('settings.org.sort.created'), value: '-created_at' },
])
const fetcher: DataFetcher<OrgItem> = (params, signal) => api.list<OrgItem>(`/org/${props.kind}`, params, { signal })
const statusFilter = computed(() => (typeof route.query.status === 'string' && !route.query.status.includes(',') ? route.query.status : null))
const pickStatus = (status: string) => void router.replace({ query: { ...route.query, status: statusFilter.value === status ? undefined : status, page: undefined } })

// The panel (`?item=`)
const openId = computed(() => (typeof route.query.item === 'string' ? route.query.item : null))
const panelOpen = computed({ get: () => !!openId.value, set: value => !value && router.replace({ query: { ...route.query, item: undefined } }) })
const ids = computed(() => (view.value?.state.rows.value ?? []).map(row => row.id))
const openRow = (row: OrgItem) => void router.replace({ query: { ...route.query, item: row.id } })
const go = (id: string) => void router.replace({ query: { ...route.query, item: id } })

// New / edit · merge · import
const editOpen = ref(false)
const editing = ref<OrgItem | null>(null)
const edit = (item: OrgItem | null) => ((editing.value = item), (editOpen.value = true))
async function saved(item: OrgItem) {
  toast.add({ title: editing.value ? t('settings.org.toast.saved', { name: item.name }) : t('settings.org.toast.created', { name: item.name }), color: 'success', icon: 'i-lucide-circle-check' })
  await refreshAll()
}
const mergeOpen = ref(false)
const merging = ref<OrgItem[]>([])
const merge = (items: OrgItem[]) => ((merging.value = items), (mergeOpen.value = true))
async function merged(item: OrgItem) {
  toast.add({ title: t('settings.org.toast.merged', { name: item.name }), color: 'success', icon: 'i-lucide-merge' })
  await refreshAll()
  openRow(item)
}
const importOpen = ref(false)
async function imported(result: OrgImportResult) {
  toast.add({ title: t('settings.org.toast.imported', { n: result.created }, result.created), description: result.skipped.length ? t('settings.org.toast.skipped', { n: result.skipped.length }, result.skipped.length) : undefined, color: 'success', icon: 'i-lucide-file-up' })
  await refreshAll()
}
async function remove(item: OrgItem) {
  if ((await actions.remove(item)) && openId.value === item.id) panelOpen.value = false
}
const rowActions = (row: OrgItem): DropdownMenuItem[][] => [
  [
    { label: t('apiService.actions.open'), icon: 'i-lucide-panel-right-open', onSelect: () => openRow(row) },
    { label: t('apiService.actions.edit'), icon: 'i-lucide-pencil', onSelect: () => edit(row) },
    { label: t('settings.org.merge.into'), icon: 'i-lucide-merge', onSelect: () => merge([row]) },
  ],
  [
    row.status === 'archived'
      ? { label: t('settings.org.restore'), icon: 'i-lucide-archive-restore', onSelect: () => void actions.restore(row) }
      : { label: t('settings.org.archive'), icon: 'i-lucide-archive', onSelect: () => void actions.archive(row) },
    { label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove(row) },
  ],
]
defineShortcuts({ n: { usingInput: false, handler: () => edit(null) } })
const initials = (name: string) => name.split(/\s+/).map(part => part[0]).join('').slice(0, 2).toUpperCase()
const existing = computed(() => (view.value?.state.rows.value ?? []).map(row => row.name))
</script>

<template>
  <SettingsPage :id="`settings-${kind}`" :plain="plain" :title="t(`settings.org.kind.${kind}.many`)" :subtitle="t(`settings.org.kind.${kind}.hint`)" :icon="SETTINGS_ORG_ICONS[kind]">
    <template #actions>
      <UButton :label="t('settings.org.importShort')" icon="i-lucide-file-up" color="neutral" variant="outline" class="hidden sm:inline-flex" @click="importOpen = true" />
      <UButton :label="t(`settings.org.kind.${kind}.new`)" icon="i-lucide-plus" color="neutral" @click="edit(null)">
        <template #trailing><UKbd value="N" size="sm" class="hidden sm:inline-flex" /></template>
      </UButton>
    </template>

    <slot name="top" />
    <SettingsOrgOverview :kind="kind" :insights="insights" :selected="statusFilter" @pick="pickStatus" />

    <DataView
      :id="`org-${kind}`"
      :key="kind"
      ref="view"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="name"
      default-view="grid"
      selectable
      :row-actions="rowActions"
      :busy="row => actions.busy.value === row.id"
      :open-row="openRow"
      :search-placeholder="t(`settings.org.kind.${kind}.search`)"
      :empty-icon="SETTINGS_ORG_ICONS[kind]"
      :empty-title="t(`settings.org.kind.${kind}.empty`)"
      :empty-description="t(`settings.org.kind.${kind}.emptyDesc`)"
    >
      <template #toolbar-start><slot name="toolbar-start" /></template>
      <template #bulk-actions="{ selected, clear }">
        <UButton :label="t('settings.org.merge.action')" icon="i-lucide-merge" color="neutral" size="sm" :disabled="selected.length < 1" @click="() => { merge(selected as OrgItem[]); clear() }" />
      </template>
      <template #name-cell="{ row }">
        <div class="flex min-w-0 flex-col">
          <span class="flex min-w-0 items-center gap-1.5">
            <UIcon v-if="row.original.status === 'active' && !row.original.members.length" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('settings.org.nobody')" />
            <span class="truncate font-medium text-highlighted">{{ row.original.name }}</span>
            <UBadge v-if="row.original.code" :label="row.original.code" color="neutral" variant="soft" size="xs" class="shrink-0 rounded-md font-mono" />
          </span>
          <span v-if="row.original.description" class="max-w-80 truncate text-xs text-muted">{{ row.original.description }}</span>
        </div>
      </template>
      <template #status-cell="{ row }"><SettingsOrgState :item="row.original" /></template>
      <template #members-cell="{ row }">
        <div class="flex items-center gap-2">
          <div class="flex items-center">
            <span v-for="(person, i) in row.original.members.slice(0, 3)" :key="person.id" class="flex size-6 items-center justify-center rounded-full border-2 border-(--ui-bg) bg-elevated text-[10px] font-semibold text-highlighted" :class="i ? '-ms-1.5' : ''" :title="person.name">{{ initials(person.name) }}</span>
          </div>
          <span class="text-muted tabular-nums">{{ t('settings.org.peopleCount', { n: number(row.original.members.length) }, row.original.members.length) }}</span>
        </div>
      </template>
      <template #forms_count-cell="{ row }"><span class="text-muted tabular-nums">{{ t('settings.org.formsCount', { n: number(row.original.forms_count) }, row.original.forms_count) }}</span></template>
      <template #updated_at-cell="{ row }"><UTooltip :text="dateTime(row.original.updated_at)"><span class="whitespace-nowrap text-muted">{{ relative(row.original.updated_at) }}</span></UTooltip></template>
      <template #created_at-cell="{ row }"><span class="whitespace-nowrap text-muted">{{ relative(row.original.created_at) }}</span></template>
      <template #empty-actions>
        <UButton :label="t(`settings.org.kind.${kind}.new`)" icon="i-lucide-plus" color="neutral" @click="edit(null)" />
        <UButton :label="t('settings.org.importShort')" icon="i-lucide-file-up" color="neutral" variant="outline" @click="importOpen = true" />
      </template>
      <template #grid-card="{ row }">
        <SettingsOrgCard :item="row" :people="insights?.people ?? 0" :actions="rowActions(row)" :busy="actions.busy.value === row.id" />
      </template>
    </DataView>

    <SettingsOrgDetail :id="openId" ref="panel" v-model:open="panelOpen" :kind="kind" :ids="ids.length ? ids : openId ? [openId] : []" :busy="!!actions.busy.value" :actions="rowActions" @go="go" @edit="edit" />
    <SettingsOrgEditModal v-model:open="editOpen" :kind="kind" :item="editing" @saved="saved" />
    <SettingsOrgMergeModal v-model:open="mergeOpen" :kind="kind" :from="merging" @merged="merged" />
    <SettingsOrgImportModal v-model:open="importOpen" :kind="kind" :existing="existing" @imported="imported" />
  </SettingsPage>
</template>
