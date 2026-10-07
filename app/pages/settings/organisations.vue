<!--
  Settings → Organisations (F14 M7, owner 2026-10-07: shared team): the subsidiaries or branches of the
  workspace, in the locked list format (rule 21): two chart cards (forms by organisation; by state with
  a legend that filters), then table / cards with search, state filter and sort; a row or card opens it
  for editing; ⋯ / right-click: edit, show its forms, archive / restore (never the main one). New (N).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { Organisation } from '#shared/types/organisations'

definePageMeta({ breadcrumb: 'settings.nav.organisations' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.organisations') })
const api = useApi()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const { relative, number } = useFormat()
const { handle } = useErrorHandler()
const organisations = useOrganisations()

// The whole list is small: loaded once, then searched, filtered, sorted and paged here
const all = ref<Organisation[] | null>(null)
async function loadAll() {
  all.value = (await api.get<Organisation[]>('/organisations', undefined, { background: !!all.value })).data
}
const view = useTemplateRef<{ refresh: () => Promise<void> }>('view')
const refreshAll = async () => {
  await loadAll()
  await view.value?.refresh()
  void organisations.load(true)
}
const fetcher: DataFetcher<Organisation> = async params => {
  if (!all.value) await loadAll()
  const q = String(params.q ?? '').trim().toLowerCase()
  const status = String(params['filter[status]'] ?? '')
  const sort = String(params.sort ?? 'name')
  const rows = all.value!.filter(item => (!q || `${item.name} ${item.short_name ?? ''} ${item.website ?? ''}`.toLowerCase().includes(q)) && (!status || status.split(',').includes(item.status)))
  const key = sort.replace(/^-/, '') as keyof Organisation
  rows.sort((a, b) => (sort.startsWith('-') ? -1 : 1) * (typeof a[key] === 'number' ? (a[key] as number) - (b[key] as number) : String(a[key]).localeCompare(String(b[key]))))
  const page = Number(params.page ?? 1)
  const perPage = Number(params.page_size ?? 20)
  return { data: rows.slice((page - 1) * perPage, page * perPage), meta: { page, page_size: perPage, total: rows.length, total_pages: Math.max(1, Math.ceil(rows.length / perPage)) } }
}

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('organisations.name'), sortable: true, fixed: true },
  { key: 'status', label: t('organisations.state'), hideBelow: 'sm' },
  { key: 'forms_count', label: t('organisations.forms'), sortable: true },
  { key: 'responses_count', label: t('organisations.responses'), sortable: true, hideBelow: 'md' },
  { key: 'updated_at', label: t('organisations.updated'), sortable: true, hideBelow: 'lg' },
])
const filters = computed<DataFilter[]>(() => [{ key: 'status', label: t('organisations.state'), icon: 'i-lucide-circle-dot', options: [{ value: 'active', label: t('organisations.active'), dot: 'bg-green-500' }, { value: 'archived', label: t('organisations.archived'), dot: 'bg-(--ui-border-accented)' }] }])
const sortOptions = computed(() => [
  { label: t('forms.sortName'), value: 'name' },
  { label: t('organisations.sortForms'), value: '-forms_count' },
  { label: t('organisations.sortResponses'), value: '-responses_count' },
  { label: t('organisations.sortUpdated'), value: '-updated_at' },
])

// Top cards
const totalForms = computed(() => (all.value ?? []).reduce((sum, item) => sum + item.forms_count, 0))
const points = computed(() => [...(all.value ?? [])].sort((a, b) => b.forms_count - a.forms_count).slice(0, 8).map(item => ({ label: item.short_name ?? item.name, value: item.forms_count })))
const statusFilter = computed(() => (typeof route.query.status === 'string' && !route.query.status.includes(',') ? route.query.status : null))
const pickStatus = (status: string) => void router.replace({ query: { ...route.query, status: statusFilter.value === status ? undefined : status, page: undefined } })
const parts = computed(() => [
  { key: 'active', label: t('organisations.active'), count: (all.value ?? []).filter(item => item.status === 'active').length, color: 'bg-green-500' },
  { key: 'archived', label: t('organisations.archived'), count: (all.value ?? []).filter(item => item.status === 'archived').length, color: 'bg-(--ui-border-accented)' },
])

// Edit · archive / restore · show its forms
const editOpen = ref(false)
const editing = ref<Organisation | null>(null)
const edit = (item: Organisation | null) => ((editing.value = item), (editOpen.value = true))
async function saved(item: Organisation) {
  toast.add({ title: editing.value ? t('organisations.saved', { name: item.name }) : t('organisations.created', { name: item.name }), color: 'success', icon: 'i-lucide-circle-check' })
  await refreshAll()
}
const busy = ref<string | null>(null)
async function setStatus(item: Organisation, archive: boolean) {
  if (busy.value) return
  busy.value = item.id
  try {
    await api.post(`/organisations/${item.id}/${archive ? 'archive' : 'restore'}`)
    toast.add({ title: t(archive ? 'organisations.archivedToast' : 'organisations.restoredToast', { name: item.name }), color: 'success', icon: archive ? 'i-lucide-archive' : 'i-lucide-archive-restore' })
    await refreshAll()
  } catch (error) {
    handle(error)
  } finally {
    busy.value = null
  }
}
const rowActions = (row: Organisation): DropdownMenuItem[][] => [
  [
    { label: t('apiService.actions.edit'), icon: 'i-lucide-pencil', onSelect: () => edit(row) },
    { label: t('organisations.showForms'), icon: 'i-lucide-file-text', disabled: row.status !== 'active', onSelect: () => organisations.choose(row.id) },
  ],
  ...(row.main ? [] : [[row.status === 'active' ? { label: t('organisations.archive'), icon: 'i-lucide-archive', onSelect: () => void setStatus(row, true) } : { label: t('organisations.restore'), icon: 'i-lucide-archive-restore', onSelect: () => void setStatus(row, false) }]]),
]
defineShortcuts({ n: { usingInput: false, handler: () => edit(null) } })
const initials = organisationInitials
</script>

<template>
  <SettingsPage id="settings-organisations" :title="t('settings.nav.organisations')" :subtitle="t('settings.desc.organisations')" icon="i-lucide-building">
    <template #actions>
      <UButton :label="t('organisations.new')" icon="i-lucide-plus" color="neutral" @click="edit(null)">
        <template #trailing><UKbd value="N" size="sm" class="hidden sm:inline-flex" /></template>
      </UButton>
    </template>

    <div class="grid shrink-0 gap-4 lg:grid-cols-2">
      <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
        <div class="flex flex-col">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('organisations.formsBy') }}</h2>
          <span class="text-xs text-muted">{{ t('organisations.formsByHint') }}</span>
        </div>
        <div v-if="!all" class="flex flex-1 items-end gap-5"><USkeleton class="h-16 w-40" /><USkeleton class="h-24 flex-1" /></div>
        <div v-else class="flex flex-1 items-end gap-5">
          <div class="flex shrink-0 flex-col gap-3">
            <div class="flex items-center gap-2.5">
              <UIcon name="i-lucide-building" class="size-5 text-muted" />
              <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(parts[0]!.count) }}</span>
              <span class="text-[11px] text-muted">{{ t('organisations.activeCount', parts[0]!.count) }}</span>
            </div>
            <dl class="flex gap-4">
              <div class="flex flex-col"><dt class="text-[11px] text-muted">{{ t('organisations.forms') }}</dt><dd class="text-sm font-medium text-highlighted tabular-nums">{{ number(totalForms) }}</dd></div>
              <div class="flex flex-col"><dt class="text-[11px] text-muted">{{ t('organisations.responses') }}</dt><dd class="text-sm font-medium text-highlighted tabular-nums">{{ number(all.reduce((sum, item) => sum + item.responses_count, 0)) }}</dd></div>
            </dl>
          </div>
          <ChartsBars v-if="points.length > 1" :points="points" height="h-24" :axis="0" :unit="n => t('organisations.formsCount', { n }, n)" class="hidden min-w-0 flex-1 sm:block" />
          <p v-else class="hidden flex-1 text-xs text-muted sm:block">{{ t('organisations.oneOnly') }}</p>
        </div>
      </UCard>
      <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('organisations.byState') }}</h2>
        <div v-if="!all" class="flex flex-1 items-end"><USkeleton class="h-24 flex-1" /></div>
        <div v-else class="flex flex-1 items-end gap-6">
          <ChartsLines :parts="parts" :selected="statusFilter" class="min-w-0 flex-1" @pick="pickStatus" />
          <ul class="hidden shrink-0 flex-col gap-1 sm:flex">
            <li v-for="part in parts" :key="part.key">
              <button type="button" class="flex w-full items-center gap-2 rounded-md px-1.5 py-0.5 text-start text-xs hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)" :class="statusFilter === part.key ? 'bg-elevated' : ''" :aria-pressed="statusFilter === part.key" @click="pickStatus(part.key)">
                <span class="size-2 shrink-0 rounded-[2px]" :class="part.color" /><span class="w-20 truncate text-default">{{ part.label }}</span><span class="ms-auto font-medium text-highlighted tabular-nums">{{ number(part.count) }}</span>
              </button>
            </li>
          </ul>
        </div>
      </UCard>
    </div>

    <DataView
      id="settings-organisations"
      ref="view"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="name"
      default-view="grid"
      :row-actions="rowActions"
      :busy="row => busy === row.id"
      :open-row="edit"
      :search-placeholder="t('organisations.search')"
      empty-icon="i-lucide-building"
      :empty-title="t('organisations.empty')"
      :empty-description="t('organisations.emptyDesc')"
    >
      <template #name-cell="{ row }">
        <div class="flex min-w-0 items-center gap-2.5">
          <span class="flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-md border border-default bg-elevated text-xs font-semibold text-highlighted">
            <img v-if="row.original.logo_url" :src="row.original.logo_url" alt="" class="max-h-full max-w-full object-contain">
            <span v-else>{{ initials(row.original) }}</span>
          </span>
          <span class="flex min-w-0 flex-col">
            <span class="flex items-center gap-1.5"><span class="truncate font-medium text-highlighted">{{ row.original.name }}</span><UBadge v-if="row.original.main" :label="t('organisations.main')" color="neutral" variant="outline" size="xs" /></span>
            <span class="truncate text-xs text-muted">{{ row.original.website ?? row.original.short_name ?? '' }}</span>
          </span>
        </div>
      </template>
      <template #status-cell="{ row }"><DataStatusBadge :status="row.original.status === 'active' ? 'active' : 'archived'" :label="row.original.status === 'active' ? t('organisations.active') : t('organisations.archived')" /></template>
      <template #forms_count-cell="{ row }"><span class="text-muted tabular-nums">{{ t('organisations.formsCount', { n: number(row.original.forms_count) }, row.original.forms_count) }}</span></template>
      <template #responses_count-cell="{ row }"><span class="text-muted tabular-nums">{{ number(row.original.responses_count) }}</span></template>
      <template #updated_at-cell="{ row }"><span class="whitespace-nowrap text-muted">{{ relative(row.original.updated_at) }}</span></template>
      <template #empty-actions><UButton :label="t('organisations.new')" icon="i-lucide-plus" color="neutral" @click="edit(null)" /></template>
      <template #grid-card="{ row }"><SettingsOrganisationsCard :item="row" :total-forms="totalForms" :actions="rowActions(row)" :busy="busy === row.id" /></template>
    </DataView>

    <SettingsOrganisationsEditModal v-model:open="editOpen" :item="editing" @saved="saved" />
  </SettingsPage>
</template>
