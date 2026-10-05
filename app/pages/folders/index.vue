<!--
  All folders (F11 M4, owner request 2026-10-02: an all-folders view with statistics). Every folder
  in the shared DataView (table / locked card; a utility list, no chart cards): folder in its
  colour, forms, published, responses in the last 30 days with a sparkline, all time, average
  completion, last activity, owners. Search and sort; a row or card opens the folder. New folder
  in the header (and the empty state); Edit and Delete (when empty) from each row's ⋯ menu.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { FolderRow, FormFolder } from '#shared/types/forms'
import { folderColor } from '#shared/utils/forms/folders'

definePageMeta({ breadcrumb: 'nav.folders' })
const { t } = useI18n()
const api = useApi()
const confirm = useConfirm()
const toast = useToast()
const counts = useNavCounts()
const { handle } = useErrorHandler()
const { relative, dateTime, number } = useFormat()
useHead({ title: () => t('nav.folders') })

const view = useTemplateRef<{ refresh: () => Promise<void> }>('view')
const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('folders.col.folder'), sortable: true, fixed: true },
  { key: 'forms_count', label: t('forms.overview.forms'), sortable: true, hideBelow: 'sm' },
  { key: 'published', label: t('status.published'), hideBelow: 'md' },
  { key: 'responses_30d', label: t('folders.responses30'), sortable: true },
  { key: 'responses_count', label: t('responses.kpi.totalLabel'), sortable: true, hideBelow: 'lg' },
  { key: 'completion_rate', label: t('forms.col.completion'), hideBelow: 'lg' },
  { key: 'last_activity_at', label: t('folders.col.activity'), sortable: true, hideBelow: 'md' },
])
const sortOptions = computed(() => [
  { label: t('forms.sortName'), value: 'name' },
  { label: t('folders.sort.forms'), value: '-forms_count' },
  { label: t('folders.sort.responses'), value: '-responses_30d' },
  { label: t('folders.sort.activity'), value: '-last_activity_at' },
])
const fetcher: DataFetcher<FolderRow> = (params, signal) => api.list<FolderRow>('/folders/overview', params, { signal })

const editing = ref<FolderRow | null>(null)
const editOpen = ref(false)
function edit(folder: FolderRow | null) {
  editing.value = folder
  editOpen.value = true
}
async function saved(folder: FormFolder) {
  await view.value?.refresh()
  if (!editing.value) await navigateTo(`/folders/${folder.id}`)
}
const busyIds = ref(new Set<string>())
async function remove(folder: FolderRow) {
  if (!(await confirm({ title: t('forms.folders.deleteTitle', { name: folder.name }), description: t('forms.folders.deleteEmpty'), danger: true }))) return
  busyIds.value = new Set([...busyIds.value, folder.id])
  try {
    await api.del(`/folders/${folder.id}`)
    toast.add({ title: t('forms.folders.deleted'), color: 'success', icon: 'i-lucide-circle-check' })
    void counts.refresh(true)
    await view.value?.refresh()
  } catch (error) {
    handle(error)
  } finally {
    busyIds.value = new Set([...busyIds.value].filter(id => id !== folder.id))
  }
}
const rowActions = (folder: FolderRow): DropdownMenuItem[][] => [
  [
    { label: t('folders.open'), icon: 'i-lucide-folder-open', to: `/folders/${folder.id}` },
    { label: t('folders.editTitle'), icon: 'i-lucide-pencil', onSelect: () => edit(folder) },
    { label: t('nav.newForm'), icon: 'i-lucide-plus', to: { path: '/forms/new', query: { folder: folder.id } } },
  ],
  [
    folder.forms_count
      ? { label: t('forms.folders.notEmpty'), icon: 'i-lucide-trash-2', disabled: true }
      : { label: t('forms.folders.deleteNamed', { name: folder.name }), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove(folder) },
  ],
]
</script>

<template>
  <AppPanel id="folders" :title="t('nav.folders')" :subtitle="t('forms.folders.desc')" subtitle-icon="i-lucide-folders">
    <template #actions>
      <UButton :label="t('forms.folders.new')" icon="i-lucide-folder-plus" color="neutral" @click="edit(null)" />
    </template>

    <DataView
      id="folders"
      ref="view"
      :columns="columns"
      :fetcher="fetcher"
      :sort-options="sortOptions"
      default-sort="name"
      default-view="grid"
      :row-actions="rowActions"
      :busy="row => busyIds.has(row.id)"
      :open-row="row => navigateTo(`/folders/${row.id}`)"
      :search-placeholder="t('folders.search')"
      empty-icon="i-lucide-folder-plus"
      :empty-title="t('folders.emptyTitle')"
      :empty-description="t('folders.emptyDesc')"
    >
      <template #name-cell="{ row }">
        <NuxtLink :to="`/folders/${row.original.id}`" class="flex min-w-0 items-center gap-2 rounded-sm focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
          <UIcon name="i-lucide-folder" class="size-4 shrink-0" :class="folderColor(row.original.color).text" />
          <span class="truncate font-medium text-highlighted">{{ row.original.name }}</span>
        </NuxtLink>
      </template>
      <template #forms_count-cell="{ row }">
        <span class="tabular-nums">{{ number(row.original.forms_count) }}</span>
      </template>
      <template #published-cell="{ row }">
        <span class="tabular-nums">{{ number(row.original.status_counts.published) }}</span>
      </template>
      <template #responses_30d-cell="{ row }">
        <div class="flex items-center gap-2">
          <span class="w-12 tabular-nums">{{ number(row.original.responses_30d) }}</span>
          <ChartsSparkline :values="(row.original as FolderRow).daily.map(day => day.count)" :width="72" :height="20" />
        </div>
      </template>
      <template #responses_count-cell="{ row }">
        <span class="tabular-nums">{{ number(row.original.responses_count) }}</span>
      </template>
      <template #completion_rate-cell="{ row }">
        <DataShareBar v-if="row.original.completion_rate !== null" :value="row.original.completion_rate / 100" />
        <span v-else class="text-muted">–</span>
      </template>
      <template #last_activity_at-cell="{ row }">
        <UTooltip v-if="row.original.last_activity_at" :text="dateTime(row.original.last_activity_at)">
          <span class="whitespace-nowrap text-muted">{{ relative(row.original.last_activity_at) }}</span>
        </UTooltip>
      </template>
      <template #empty-actions>
        <UButton :label="t('forms.folders.new')" icon="i-lucide-folder-plus" color="neutral" @click="edit(null)" />
      </template>
      <template #grid-card="{ row }">
        <FoldersCard :folder="row" :actions="rowActions(row)" />
      </template>
    </DataView>

    <FoldersEditModal v-model:open="editOpen" :folder="editing" @saved="saved" />
  </AppPanel>
</template>
