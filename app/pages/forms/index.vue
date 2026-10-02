<!--
  Forms list (F6): DataView (search, status / folder / owner / tag filters, date range, sort,
  Table / Grid) · inline rename · duplicate · move · tags · lifecycle · delete to Trash · bulk.
  Busy rows while an action runs; every action refreshes the list and the sidebar counts.
-->
<script setup lang="ts">
import type { FormFacets, FormFolder, FormSummary } from '#shared/types/forms'

definePageMeta({ breadcrumb: 'nav.forms' })

const { t } = useI18n()
const api = useApi()
const { relative, date, number } = useFormat()
useHead({ title: () => t('nav.forms') })

const dataView = useTemplateRef<{ refresh: () => Promise<void> }>('dataView')
const folders = ref<FormFolder[]>([])
const facets = ref<FormFacets>({ owners: [], tags: [] })
const foldersLoading = ref(false)

async function loadMeta() {
  foldersLoading.value = true
  try {
    const [folderList, facetList] = await Promise.all([
      api.get<FormFolder[]>('/folders', undefined, { background: true }),
      api.get<FormFacets>('/forms/facets', undefined, { background: true }),
    ])
    folders.value = folderList.data
    facets.value = facetList.data
  } catch {
    // Filters simply stay empty; the list reports its own errors.
  } finally {
    foldersLoading.value = false
  }
}
onMounted(loadMeta)

const refresh = async () => {
  await Promise.all([dataView.value?.refresh(), loadMeta()])
}
const actions = useFormActions(refresh)

// ── Inline rename, move and tags ───────────────────────────────────────────────────
const renamingId = ref<string | null>(null)
const moveTargets = ref<FormSummary[]>([])
const moveOpen = ref(false)
const tagsTarget = ref<FormSummary | null>(null)
const tagsOpen = ref(false)
const foldersOpen = ref(false)

const rowActions = useFormMenu(actions, {
  rename: form => (renamingId.value = form.id),
  move: form => {
    moveTargets.value = [form]
    moveOpen.value = true
  },
  tags: form => {
    tagsTarget.value = form
    tagsOpen.value = true
  },
})

async function onRename(form: FormSummary, name: string) {
  renamingId.value = null
  await actions.rename(form, name)
}
async function onMove(folderId: string | null) {
  const targets = moveTargets.value
  if (targets.length === 1) await actions.move(targets[0]!, folderId)
  else await actions.bulk('move', targets, folderId)
}

// ── List definition ────────────────────────────────────────────────────────────────
const STATUS_DOTS: Record<string, string> = {
  draft: 'bg-amber-500',
  published: 'bg-green-500',
  closed: 'bg-violet-600',
  archived: 'bg-(--ui-text-dimmed)',
}

const filters = computed<DataFilter[]>(() => [
  {
    key: 'status',
    label: t('forms.filterStatus'),
    options: Object.keys(STATUS_DOTS).map(value => ({
      value,
      label: t(`status.${value}`),
      dot: STATUS_DOTS[value],
    })),
  },
  {
    key: 'folder_id',
    label: t('forms.filterFolder'),
    options: [
      { value: 'none', label: t('forms.noFolder') },
      ...folders.value.map(folder => ({ value: folder.id, label: folder.name })),
    ],
  },
  {
    key: 'owner_id',
    label: t('forms.filterOwner'),
    options: facets.value.owners.map(owner => ({ value: owner.id, label: owner.name })),
  },
  {
    key: 'tag',
    label: t('forms.filterTag'),
    options: facets.value.tags.map(tag => ({ value: tag, label: tag })),
  },
])

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('forms.col.name'), sortable: true },
  { key: 'status', label: t('forms.col.status') },
  { key: 'owner', label: t('forms.col.owner'), hideBelow: 'lg' },
  { key: 'completion_rate', label: t('forms.col.completion'), sortable: true, hideBelow: 'md' },
  {
    key: 'responses_count',
    label: t('forms.col.responses'),
    sortable: true,
    hideBelow: 'sm',
    class: 'text-end',
  },
  { key: 'updated_at', label: t('forms.col.updated'), sortable: true, hideBelow: 'sm' },
])

const sortOptions = computed(() => [
  { label: t('forms.sortRecent'), value: '-updated_at' },
  { label: t('forms.sortOldest'), value: 'updated_at' },
  { label: t('forms.sortName'), value: 'name' },
  { label: t('forms.sortResponses'), value: '-responses_count' },
])

const fetcher: DataFetcher<FormSummary> = (params, signal) =>
  api.list<FormSummary>('/forms', params, { signal })

defineShortcuts({ n: () => navigateTo('/forms/new') })
</script>

<template>
  <AppPanel
    id="forms"
    :title="t('nav.forms')"
    :subtitle="t('forms.description')"
    subtitle-icon="i-lucide-refresh-cw"
  >
    <template #actions>
      <UButton
        icon="i-lucide-folder-cog"
        :label="t('forms.folders.button')"
        color="neutral"
        variant="outline"
        @click="foldersOpen = true"
      />
      <UButton
        icon="i-lucide-upload"
        :label="t('forms.import')"
        color="neutral"
        variant="outline"
        :to="{ path: '/forms/new', query: { mode: 'import' } }"
      />
      <UButton icon="i-lucide-plus" :label="t('nav.newForm')" color="neutral" to="/forms/new">
        <template #trailing>
          <UKbd value="N" class="hidden lg:inline-flex" />
        </template>
      </UButton>
    </template>

    <DataView
      id="forms"
      ref="dataView"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="-updated_at"
      date-range
      selectable
      :row-actions="rowActions"
      :busy="actions.isBusy"
      :search-placeholder="t('forms.searchPlaceholder')"
      empty-icon="i-lucide-file-text"
      :empty-title="t('forms.emptyTitle')"
      :empty-description="t('forms.emptyDesc')"
    >
      <template #name-cell="{ row }">
        <FormsListNameCell
          :form="row.original"
          :editing="renamingId === row.original.id"
          :busy="actions.isBusy(row.original)"
          @save="name => onRename(row.original, name)"
          @cancel="renamingId = null"
        />
      </template>
      <template #status-cell="{ row }">
        <DataStatusBadge :status="row.original.status" />
      </template>
      <template #owner-cell="{ row }">
        <UUser :name="row.original.owner.name" :avatar="{ alt: row.original.owner.name }" size="xs" />
      </template>
      <template #completion_rate-cell="{ row }">
        <div v-if="row.original.status !== 'draft'" class="flex min-w-32 items-center gap-2">
          <UProgress :model-value="row.original.completion_rate" color="neutral" size="sm" class="flex-1" />
          <span class="w-9 text-end text-xs text-muted">{{ row.original.completion_rate }}%</span>
        </div>
        <span v-else class="text-xs text-muted">{{ t('forms.notStarted') }}</span>
      </template>
      <template #responses_count-cell="{ row }">
        <span class="tabular-nums">{{ number(row.original.responses_count) }}</span>
      </template>
      <template #updated_at-cell="{ row }">
        <UTooltip :text="date(row.original.updated_at, 'full')">
          <span class="whitespace-nowrap">{{ relative(row.original.updated_at) }}</span>
        </UTooltip>
      </template>

      <template #grid-card="{ row }">
        <FormsListCard :form="row" :actions="rowActions(row)" :busy="actions.isBusy(row)" />
      </template>

      <template #bulk-actions="{ selected, clear }">
        <UButton
          :label="t('forms.actions.move')"
          icon="i-lucide-folder-input"
          color="neutral"
          variant="outline"
          size="sm"
          @click="((moveTargets = selected), (moveOpen = true))"
        />
        <UButton
          :label="t('forms.actions.archive')"
          icon="i-lucide-archive"
          color="neutral"
          variant="outline"
          size="sm"
          :loading="selected.some(actions.isBusy)"
          @click="actions.bulk('archive', selected).then(done => done && clear())"
        />
        <UButton
          :label="t('forms.actions.delete')"
          icon="i-lucide-trash-2"
          color="error"
          variant="outline"
          size="sm"
          :loading="selected.some(actions.isBusy)"
          @click="actions.bulk('delete', selected).then(done => done && clear())"
        />
      </template>

      <template #empty-actions>
        <UButton icon="i-lucide-plus" :label="t('nav.newForm')" color="neutral" to="/forms/new" />
        <UButton
          icon="i-lucide-layout-template"
          :label="t('nav.fromTemplate')"
          color="neutral"
          variant="outline"
          :to="{ path: '/forms/new', query: { mode: 'template' } }"
        />
      </template>
    </DataView>

    <FormsListMoveModal
      v-model:open="moveOpen"
      :folders="folders"
      :count="moveTargets.length"
      :current="moveTargets.length === 1 ? (moveTargets[0]?.folder?.id ?? null) : undefined"
      @move="onMove"
      @folder-created="loadMeta"
    />
    <FormsListTagsModal
      v-model:open="tagsOpen"
      :tags="tagsTarget?.tags ?? []"
      :suggestions="facets.tags"
      :form-name="tagsTarget?.name ?? ''"
      @save="tags => tagsTarget && actions.setTags(tagsTarget, tags)"
    />
    <FormsListFoldersModal
      v-model:open="foldersOpen"
      :folders="folders"
      :loading="foldersLoading"
      @changed="refresh"
    />
  </AppPanel>
</template>
