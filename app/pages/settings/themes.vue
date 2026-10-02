<!--
  Themes library (F8, Resources → Themes): saved designs of the workspace in the shared DataView —
  table or grid with mini previews, search, sort; rename, duplicate, delete (forms keep their copy).
  New themes are saved from any form's Design view.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { SavedTheme } from '#shared/types/forms'

definePageMeta({ breadcrumb: 'nav.themes' })
const { t } = useI18n()
const api = useApi()
const { relative, dateTime } = useFormat()
const confirm = useConfirm()
const library = useThemes()
useHead({ title: () => t('nav.themes') })

const dataView = useTemplateRef<{ refresh: () => Promise<void> }>('dataView')
const busy = ref(new Set<string>())
async function act(theme: SavedTheme, work: () => Promise<unknown>) {
  busy.value = new Set(busy.value).add(theme.id)
  try {
    await work()
    await dataView.value?.refresh()
  } finally {
    const next = new Set(busy.value)
    next.delete(theme.id)
    busy.value = next
  }
}

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('themes.col.name'), sortable: true },
  { key: 'forms_count', label: t('themes.col.forms'), hideBelow: 'sm' },
  { key: 'created_by', label: t('themes.col.createdBy'), hideBelow: 'md' },
  { key: 'updated_at', label: t('themes.col.updated'), sortable: true, hideBelow: 'sm' },
])
const sortOptions = computed(() => [
  { label: t('themes.sortRecent'), value: '-updated_at' },
  { label: t('themes.sortName'), value: 'name' },
])
const fetcher: DataFetcher<SavedTheme> = (params, signal) => api.list<SavedTheme>('/themes', params, { signal })

const renaming = ref<SavedTheme | null>(null)
const renameOpen = ref(false)
function rename(theme: SavedTheme) {
  renaming.value = theme
  renameOpen.value = true
}
async function remove(theme: SavedTheme) {
  const ok = await confirm({
    title: t('themes.deleteTitle', { name: theme.name }),
    description: theme.forms_count ? t('themes.deleteUsed', { count: theme.forms_count }, theme.forms_count) : t('themes.deleteDesc'),
    danger: true,
    confirmLabel: t('themes.delete'),
  })
  if (ok) await act(theme, () => library.remove(theme))
}

const rowActions = (theme: SavedTheme): DropdownMenuItem[][] => [
  [
    { label: t('themes.rename'), icon: 'i-lucide-pencil', onSelect: () => rename(theme) },
    { label: t('themes.duplicate'), icon: 'i-lucide-copy', onSelect: () => void act(theme, () => library.duplicate(theme)) },
  ],
  [{ label: t('themes.delete'), icon: 'i-lucide-trash-2', color: 'error', onSelect: () => void remove(theme) }],
]
const isBusy = (theme: SavedTheme) => busy.value.has(theme.id)
</script>

<template>
  <AppPanel id="themes" :title="t('nav.themes')" :subtitle="t('themes.subtitle')" subtitle-icon="i-lucide-palette">
    <template #actions>
      <UButton :label="t('themes.goToForms')" icon="i-lucide-file-text" color="neutral" variant="outline" to="/forms" />
    </template>

    <DataView
      id="themes"
      ref="dataView"
      :columns="columns"
      :fetcher="fetcher"
      :sort-options="sortOptions"
      default-sort="-updated_at"
      :row-actions="rowActions"
      :busy="isBusy"
      :search-placeholder="t('themes.search')"
      empty-icon="i-lucide-palette"
      :empty-title="t('themes.emptyTitle')"
      :empty-description="t('themes.emptyDesc')"
    >
      <template #name-cell="{ row }">
        <div class="flex min-w-0 items-center gap-3">
          <FormsDesignerSwatch :theme="row.original.tokens" size="sm" />
          <span class="flex min-w-0 items-center gap-1.5 truncate font-medium text-highlighted">
            <UIcon v-if="isBusy(row.original)" name="i-lucide-loader-circle" class="size-3.5 shrink-0 animate-spin text-muted" />
            {{ row.original.name }}
          </span>
        </div>
      </template>
      <template #forms_count-cell="{ row }">
        <span class="text-muted">{{ t('themes.formsCount', { count: row.original.forms_count }, row.original.forms_count) }}</span>
      </template>
      <template #created_by-cell="{ row }">
        <UUser :name="row.original.created_by.name" :avatar="{ alt: row.original.created_by.name }" size="xs" />
      </template>
      <template #updated_at-cell="{ row }">
        <UTooltip :text="dateTime(row.original.updated_at)">
          <span class="whitespace-nowrap">{{ relative(row.original.updated_at) }}</span>
        </UTooltip>
      </template>

      <template #grid-card="{ row }">
        <UCard :ui="{ body: 'flex flex-col gap-3 p-3 sm:p-3' }" class="h-full" :class="isBusy(row) ? 'opacity-60' : ''">
          <FormsDesignerSwatch :theme="row.tokens" />
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <p class="truncate font-semibold text-highlighted">{{ row.name }}</p>
              <p class="truncate text-xs text-muted">
                {{ t('themes.formsCount', { count: row.forms_count }, row.forms_count) }} · {{ relative(row.updated_at) }}
              </p>
            </div>
            <UDropdownMenu :items="rowActions(row)" :content="{ align: 'end' }">
              <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="xs" square :loading="isBusy(row)" :aria-label="t('dataView.actions')" />
            </UDropdownMenu>
          </div>
        </UCard>
      </template>
    </DataView>

    <FormsDesignerRenameThemeModal v-model:open="renameOpen" :theme="renaming" @saved="dataView?.refresh()" />
  </AppPanel>
</template>
