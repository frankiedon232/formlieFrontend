<!-- Trash (F6): deleted forms for 30 days — restore, delete permanently (confirm), bulk, empty Trash. -->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import { TRASH_RETENTION_DAYS, type FormSummary } from '#shared/types/forms'

definePageMeta({ breadcrumb: 'forms.trash.title' })

const { t } = useI18n()
const api = useApi()
const { relative, dateTime } = useFormat()
const { counts } = useNavCounts()
useHead({ title: () => t('forms.trash.title') })

const dataView = useTemplateRef<{ refresh: () => Promise<void> }>('dataView')
const actions = useFormActions(async () => {
  await dataView.value?.refresh()
})
const trashCount = computed(() => counts.value?.forms.trash ?? 0)

const daysLeft = (form: FormSummary) =>
  Math.max(
    0,
    Math.ceil((Date.parse(form.deleted_at ?? '') + TRASH_RETENTION_DAYS * 86_400_000 - Date.now()) / 86_400_000),
  )

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('forms.col.name'), sortable: true },
  { key: 'owner', label: t('forms.col.owner'), hideBelow: 'md' },
  { key: 'deleted_at', label: t('forms.trash.deleted'), sortable: true, hideBelow: 'sm' },
  { key: 'days_left', label: t('forms.trash.daysLeft') },
])
const sortOptions = computed(() => [
  { label: t('forms.trash.sortRecent'), value: '-deleted_at' },
  { label: t('forms.sortName'), value: 'name' },
])

const fetcher: DataFetcher<FormSummary> = (params, signal) =>
  api.list<FormSummary>('/forms', { ...params, 'filter[trash]': '1' }, { signal })

const rowActions = (form: FormSummary): DropdownMenuItem[][] => [
  [
    {
      label: t('forms.actions.restore'),
      icon: 'i-lucide-undo-2',
      onSelect: () => actions.lifecycle(form, 'restore'),
    },
  ],
  [
    {
      label: t('forms.actions.purge'),
      icon: 'i-lucide-trash',
      color: 'error',
      onSelect: () => actions.purge(form),
    },
  ],
]
</script>

<template>
  <AppPanel
    id="forms-trash"
    :title="t('forms.trash.title')"
    :subtitle="t('forms.trash.subtitle', { days: TRASH_RETENTION_DAYS })"
    subtitle-icon="i-lucide-clock"
  >
    <template #actions>
      <UButton
        icon="i-lucide-trash"
        :label="t('forms.trash.empty')"
        color="error"
        variant="outline"
        :disabled="!trashCount"
        :loading="actions.busyIds.value.has('__trash__')"
        @click="actions.emptyTrash(trashCount)"
      />
    </template>

    <DataView
      id="forms-trash"
      ref="dataView"
      :columns="columns"
      :fetcher="fetcher"
      :sort-options="sortOptions"
      default-sort="-deleted_at"
      selectable
      :row-actions="rowActions"
      :busy="actions.isBusy"
      :search-placeholder="t('forms.searchPlaceholder')"
      empty-icon="i-lucide-trash-2"
      :empty-title="t('forms.trash.emptyTitle')"
      :empty-description="t('forms.trash.emptyDesc', { days: TRASH_RETENTION_DAYS })"
    >
      <template #name-cell="{ row }">
        <div class="min-w-0">
          <p class="flex items-center gap-1.5 truncate font-medium text-highlighted">
            <UIcon
              v-if="actions.isBusy(row.original)"
              name="i-lucide-loader-circle"
              class="size-3.5 shrink-0 animate-spin text-muted"
            />
            {{ row.original.name }}
          </p>
          <p class="truncate text-xs text-muted">{{ row.original.folder?.name ?? t('forms.noFolder') }}</p>
        </div>
      </template>
      <template #owner-cell="{ row }">
        <UUser :name="row.original.owner.name" :avatar="{ alt: row.original.owner.name }" size="xs" />
      </template>
      <template #deleted_at-cell="{ row }">
        <UTooltip :text="dateTime(row.original.deleted_at)">
          <span class="whitespace-nowrap">{{ relative(row.original.deleted_at) }}</span>
        </UTooltip>
      </template>
      <template #days_left-cell="{ row }">
        <UBadge
          :label="t('forms.trash.days', { count: daysLeft(row.original) }, daysLeft(row.original))"
          :color="daysLeft(row.original) <= 3 ? 'warning' : 'neutral'"
          variant="subtle"
          size="sm"
          class="rounded-md"
        />
      </template>

      <template #grid-card="{ row }">
        <UCard :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-4' }" class="h-full">
          <div class="flex items-start justify-between gap-2">
            <p class="min-w-0 truncate font-semibold text-highlighted">{{ row.name }}</p>
            <UDropdownMenu :items="rowActions(row)" :content="{ align: 'end' }">
              <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="xs" square :aria-label="t('dataView.actions')" />
            </UDropdownMenu>
          </div>
          <p class="text-sm text-muted">{{ t('forms.trash.deletedAgo', { time: relative(row.deleted_at) }) }}</p>
          <UBadge
            :label="t('forms.trash.days', { count: daysLeft(row) }, daysLeft(row))"
            :color="daysLeft(row) <= 3 ? 'warning' : 'neutral'"
            variant="subtle"
            size="sm"
            class="mt-auto self-start rounded-md"
          />
        </UCard>
      </template>

      <template #bulk-actions="{ selected, clear }">
        <UButton
          :label="t('forms.actions.restore')"
          icon="i-lucide-undo-2"
          color="neutral"
          variant="outline"
          size="sm"
          :loading="selected.some(actions.isBusy)"
          @click="actions.bulk('restore', selected).then(done => done && clear())"
        />
        <UButton
          :label="t('forms.actions.purge')"
          icon="i-lucide-trash"
          color="error"
          variant="outline"
          size="sm"
          :loading="selected.some(actions.isBusy)"
          @click="actions.bulk('purge', selected).then(done => done && clear())"
        />
      </template>
    </DataView>
  </AppPanel>
</template>
