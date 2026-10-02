<!--
  Forms list (DataView demo for F2; create / duplicate / archive / trash arrive in F6).
  Layout follows docs/design: page header + "All forms" table with filters, date range, sort, Table/Grid.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { FormFolder, FormSummary } from '#shared/types/forms'

definePageMeta({ breadcrumb: 'nav.forms' })

const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { copy } = useClipboard({ legacy: true })
const { date, relative, number } = useFormat()
const requestUrl = useRequestURL()
useHead({ title: () => t('nav.forms') })

const folders = ref<FormFolder[]>([])
onMounted(async () => {
  try {
    folders.value = (await api.get<FormFolder[]>('/folders')).data
  } catch {
    // The folder filter simply stays empty; the list itself reports its own errors.
  }
})

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
    options: folders.value.map(folder => ({ value: folder.id, label: folder.name })),
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

function rowActions(form: FormSummary): DropdownMenuItem[][] {
  return [
    [
      {
        label: t('forms.copyLink'),
        icon: 'i-lucide-link',
        onSelect: () => {
          copy(`${requestUrl.origin}/f/${form.slug}`)
          toast.add({ title: t('forms.linkCopied'), color: 'success', icon: 'i-lucide-check' })
        },
      },
      { label: t('forms.viewResponses'), icon: 'i-lucide-inbox', to: `/responses?form=${form.id}` },
    ],
  ]
}
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
        icon="i-lucide-upload"
        :label="t('forms.import')"
        color="neutral"
        variant="outline"
        to="/forms/new"
      />
      <UButton icon="i-lucide-plus" :label="t('nav.newForm')" color="neutral" to="/forms/new" />
    </template>

    <DataView
      id="forms"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="-updated_at"
      date-range
      selectable
      :row-actions="rowActions"
      :search-placeholder="t('forms.searchPlaceholder')"
      empty-icon="i-lucide-file-text"
      :empty-title="t('forms.emptyTitle')"
      :empty-description="t('forms.emptyDesc')"
    >
      <template #name-cell="{ row }">
        <div class="min-w-0">
          <p class="truncate font-medium text-highlighted">{{ row.original.name }}</p>
          <p class="truncate text-xs text-muted">
            {{ row.original.folder?.name ?? t('forms.noFolder') }}
            <span v-if="row.original.has_unpublished_changes"> · {{ t('forms.unpublished') }}</span>
          </p>
        </div>
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
        <FormsListCard :form="row" :actions="rowActions(row)" />
      </template>

      <template #empty-actions>
        <UButton icon="i-lucide-plus" :label="t('nav.newForm')" color="neutral" to="/forms/new" />
        <UButton
          icon="i-lucide-layout-template"
          :label="t('nav.fromTemplate')"
          color="neutral"
          variant="outline"
          to="/templates"
        />
      </template>
    </DataView>
  </AppPanel>
</template>
