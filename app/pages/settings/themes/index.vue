<!--
  Themes library (Resources → Themes): three kinds in the shared DataView, System (Formalie's
  designs, read-only: duplicate to change), Saved (from a form's design) and Created (theme editor).
  Table or grid with page-shaped previews, filter by kind, search, sort; edit, rename, duplicate,
  delete (forms keep their copy). Locked table / grid format (rule 21; owner 2026-10-04: no chart cards here): the table with
  Columns and a share bar, the locked card; a row or card opens the theme.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { SavedTheme, ThemeInsights } from '#shared/types/forms'

definePageMeta({ breadcrumb: 'nav.themes' })
const { t } = useI18n()
const api = useApi()
const { relative, dateTime } = useFormat()
const confirm = useConfirm()
const library = useThemes()
useHead({ title: () => t('nav.themes') })

const dataView = useTemplateRef<{ refresh: () => Promise<void> }>('dataView')
const insights = ref<ThemeInsights | null>(null)
async function loadInsights() {
  try {
    insights.value = (await api.get<ThemeInsights>('/themes/insights', undefined, { background: true })).data
  } catch {
    // Share bars show 0 %; the list reports its own errors.
  }
}
onMounted(loadInsights)
const busy = ref(new Set<string>())
async function act(theme: SavedTheme, work: () => Promise<unknown>) {
  busy.value = new Set(busy.value).add(theme.id)
  try {
    await work()
    await Promise.all([dataView.value?.refresh(), loadInsights()])
  } finally {
    const next = new Set(busy.value)
    next.delete(theme.id)
    busy.value = next
  }
}

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('themes.col.name'), sortable: true, fixed: true },
  { key: 'forms_count', label: t('themes.col.forms'), hideBelow: 'sm' },
  { key: 'share', label: t('themes.card.share'), hideBelow: 'lg' },
  { key: 'created_by', label: t('themes.col.createdBy'), hideBelow: 'md' },
  { key: 'updated_at', label: t('themes.col.updated'), sortable: true, hideBelow: 'sm' },
])
const sortOptions = computed(() => [
  { label: t('themes.sortRecent'), value: '-updated_at' },
  { label: t('themes.sortName'), value: 'name' },
])
const fetcher: DataFetcher<SavedTheme> = (params, signal) =>
  api.list<SavedTheme>('/themes', params, { signal })
const SOURCE_ICON: Record<SavedTheme['source'], string> = {
  system: 'i-lucide-sparkles',
  saved: 'i-lucide-bookmark',
  created: 'i-lucide-paintbrush',
}
const sourceIcon = (source: string) => SOURCE_ICON[source as SavedTheme['source']] ?? 'i-lucide-palette'
const filters = computed<DataFilter[]>(() => [
  {
    key: 'source',
    label: t('themes.filterSource'),
    icon: 'i-lucide-library',
    options: (['system', 'saved', 'created'] as const).map(value => ({
      value,
      label: t(`themes.source.${value}`),
    })),
  },
])
const name = (theme: SavedTheme) => library.nameOf(theme)
const preview = computed(() => [
  t('themes.previewName'),
  t('themes.previewEmail'),
  t('themes.previewMessage'),
])

const renaming = ref<SavedTheme | null>(null)
const renameOpen = ref(false)
function rename(theme: SavedTheme) {
  renaming.value = theme
  renameOpen.value = true
}
async function remove(theme: SavedTheme) {
  const ok = await confirm({
    title: t('themes.deleteTitle', { name: name(theme) }),
    description: theme.forms_count
      ? t('themes.deleteUsed', { count: theme.forms_count }, theme.forms_count)
      : t('themes.deleteDesc'),
    danger: true,
    confirmLabel: t('themes.delete'),
  })
  if (ok) await act(theme, () => library.remove(theme))
}

async function duplicateToEdit(theme: SavedTheme) {
  busy.value = new Set(busy.value).add(theme.id)
  try {
    const copy = await library.duplicate({ ...theme, name: name(theme) })
    if (copy) await navigateTo(`/settings/themes/${copy.id}`)
  } finally {
    const next = new Set(busy.value)
    next.delete(theme.id)
    busy.value = next
  }
}
const rowActions = (theme: SavedTheme): DropdownMenuItem[][] =>
  theme.source === 'system'
    ? [
        [
          { label: t('themes.view'), icon: 'i-lucide-eye', to: `/settings/themes/${theme.id}` },
          {
            label: t('themes.duplicateToEdit'),
            icon: 'i-lucide-copy-plus',
            onSelect: () => void duplicateToEdit(theme),
          },
        ],
      ]
    : [
        [
          { label: t('themes.editDesign'), icon: 'i-lucide-paintbrush', to: `/settings/themes/${theme.id}` },
          { label: t('themes.rename'), icon: 'i-lucide-pencil', onSelect: () => rename(theme) },
          {
            label: t('themes.duplicate'),
            icon: 'i-lucide-copy',
            onSelect: () => void act(theme, () => library.duplicate(theme)),
          },
        ],
        [
          {
            label: t('themes.delete'),
            icon: 'i-lucide-trash-2',
            color: 'error',
            onSelect: () => void remove(theme),
          },
        ],
      ]
const isBusy = (theme: SavedTheme) => busy.value.has(theme.id)
/** After a rename: the list and the top cards. */
const refreshAll = () => Promise.all([dataView.value?.refresh(), loadInsights()])
</script>

<template>
  <AppPanel
    id="themes"
    :title="t('nav.themes')"
    :subtitle="t('themes.subtitle')"
    subtitle-icon="i-lucide-palette"
  >
    <template #actions>
      <UButton
        :label="t('themes.goToForms')"
        icon="i-lucide-file-text"
        color="neutral"
        variant="outline"
        to="/forms"
      />
      <UButton :label="t('themes.newTheme')" icon="i-lucide-plus" color="neutral" to="/settings/themes/new" />
    </template>

    <div class="flex flex-col gap-4">
      <DataView
        id="themes"
        ref="dataView"
        :columns="columns"
        :fetcher="fetcher"
        :filters="filters"
        :sort-options="sortOptions"
        default-sort="-updated_at"
        :row-actions="rowActions"
        :busy="isBusy"
        :open-row="row => navigateTo(`/settings/themes/${row.id}`)"
        :search-placeholder="t('themes.search')"
        empty-icon="i-lucide-palette"
        :empty-title="t('themes.emptyTitle')"
        :empty-description="t('themes.emptyDesc')"
      >
        <template #name-cell="{ row }">
          <NuxtLink
            :to="`/settings/themes/${row.original.id}`"
            class="flex min-w-0 items-center gap-3 rounded-sm focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
          >
            <span class="w-16 shrink-0 overflow-hidden rounded-sm border border-default">
              <TemplatesThumb
                :theme="row.original.tokens"
                :title="name(row.original)"
                :labels="preview"
                mini
              />
            </span>
            <span class="flex min-w-0 flex-col">
              <span class="flex min-w-0 items-center gap-1.5 truncate font-medium text-highlighted">
                <UIcon
                  v-if="isBusy(row.original)"
                  name="i-lucide-loader-circle"
                  class="size-3.5 shrink-0 animate-spin text-muted"
                />
                {{ name(row.original) }}
              </span>
              <span class="flex items-center gap-1 text-xs text-muted">
                <UIcon :name="sourceIcon(row.original.source)" class="size-3" />{{
                  t(`themes.source.${row.original.source}`)
                }}
              </span>
            </span>
          </NuxtLink>
        </template>
        <template #forms_count-cell="{ row }">
          <span class="text-default">{{
            t('themes.formsCount', { count: row.original.forms_count }, row.original.forms_count)
          }}</span>
        </template>
        <template #share-cell="{ row }">
          <DataShareBar
            :value="insights?.forms_total ? row.original.forms_count / insights.forms_total : 0"
          />
        </template>
        <template #created_by-cell="{ row }">
          <UUser
            :name="row.original.created_by.name"
            :avatar="{ alt: row.original.created_by.name }"
            size="xs"
          />
        </template>
        <template #updated_at-cell="{ row }">
          <UTooltip :text="dateTime(row.original.updated_at)">
            <span class="whitespace-nowrap">{{ relative(row.original.updated_at) }}</span>
          </UTooltip>
        </template>

        <template #grid-card="{ row }">
          <ThemesCard
            :theme="row"
            :name="name(row)"
            :actions="rowActions(row)"
            :busy="isBusy(row)"
            :preview="preview"
          />
        </template>
      </DataView>
    </div>

    <FormsDesignerRenameThemeModal
      v-model:open="renameOpen"
      :theme="renaming"
      @saved="refreshAll"
    />
  </AppPanel>
</template>
