<!--
  Page designs library (Resources → Pages; owner 2026-10-04: "add more pages, just like Themes"):
  the page around a form on its public link. Three kinds in the shared DataView: Formalie's
  (read-only: duplicate to change), Saved (from a form's design) and Created (page editor). Same
  table / grid format as Themes (rule 21, no chart cards): miniature, forms using it, share of
  forms, author, changed; the locked card; a row or card opens the design. Forms keep their copy.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { PageDesign, PageDesignInsights } from '#shared/types/forms'

definePageMeta({ breadcrumb: 'nav.pages' })
const { t } = useI18n()
const api = useApi()
const { relative, dateTime } = useFormat()
const confirm = useConfirm()
const library = usePageDesigns()
useHead({ title: () => t('nav.pages') })

const dataView = useTemplateRef<{ refresh: () => Promise<void> }>('dataView')
const insights = ref<PageDesignInsights | null>(null)
async function loadInsights() {
  try {
    insights.value = (await api.get<PageDesignInsights>('/page-designs/insights', undefined, { background: true })).data
  } catch {
    // Share bars show 0 %; the list reports its own errors.
  }
}
onMounted(loadInsights)

const busy = ref(new Set<string>())
async function act(page: PageDesign, work: () => Promise<unknown>) {
  busy.value = new Set(busy.value).add(page.id)
  try {
    await work()
    await Promise.all([dataView.value?.refresh(), loadInsights()])
  } finally {
    const next = new Set(busy.value)
    next.delete(page.id)
    busy.value = next
  }
}

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('pages.col.name'), sortable: true, fixed: true },
  { key: 'style', label: t('pages.col.style'), hideBelow: 'md' },
  { key: 'forms_count', label: t('themes.col.forms'), hideBelow: 'sm' },
  { key: 'share', label: t('themes.card.share'), hideBelow: 'lg' },
  { key: 'created_by', label: t('themes.col.createdBy'), hideBelow: 'lg' },
  { key: 'updated_at', label: t('themes.col.updated'), sortable: true, hideBelow: 'sm' },
])
const sortOptions = computed(() => [
  { label: t('themes.sortRecent'), value: '-updated_at' },
  { label: t('themes.sortName'), value: 'name' },
])
const fetcher: DataFetcher<PageDesign> = (params, signal) => api.list<PageDesign>('/page-designs', params, { signal })
const SOURCE_ICON: Record<PageDesign['source'], string> = { system: 'i-lucide-sparkles', saved: 'i-lucide-bookmark', created: 'i-lucide-paintbrush' }
const filters = computed<DataFilter[]>(() => [
  { key: 'source', label: t('themes.filterSource'), icon: 'i-lucide-library', options: (['system', 'saved', 'created'] as const).map(value => ({ value, label: t(`themes.source.${value}`) })) },
])
const name = (page: PageDesign) => library.nameOf(page)

async function remove(page: PageDesign) {
  const ok = await confirm({
    title: t('pages.deleteTitle', { name: name(page) }),
    description: page.forms_count ? t('themes.deleteUsed', { count: page.forms_count }, page.forms_count) : t('pages.deleteDesc'),
    danger: true,
    confirmLabel: t('themes.delete'),
  })
  if (ok) await act(page, () => library.remove(page))
}
async function duplicateToEdit(page: PageDesign) {
  busy.value = new Set(busy.value).add(page.id)
  try {
    const copy = await library.duplicate({ ...page, name: name(page) })
    if (copy) await navigateTo(`/settings/pages/${copy.id}`)
  } finally {
    const next = new Set(busy.value)
    next.delete(page.id)
    busy.value = next
  }
}
const rowActions = (page: PageDesign): DropdownMenuItem[][] =>
  page.source === 'system'
    ? [
        [
          { label: t('themes.view'), icon: 'i-lucide-eye', to: `/settings/pages/${page.id}` },
          { label: t('themes.duplicateToEdit'), icon: 'i-lucide-copy-plus', onSelect: () => void duplicateToEdit(page) },
        ],
      ]
    : [
        [
          { label: t('themes.editDesign'), icon: 'i-lucide-paintbrush', to: `/settings/pages/${page.id}` },
          { label: t('themes.duplicate'), icon: 'i-lucide-copy', onSelect: () => void act(page, () => library.duplicate({ ...page, name: name(page) })) },
        ],
        [{ label: t('themes.delete'), icon: 'i-lucide-trash-2', color: 'error', onSelect: () => void remove(page) }],
      ]
const isBusy = (page: PageDesign) => busy.value.has(page.id)
</script>

<template>
  <AppPanel id="pages" :title="t('nav.pages')" :subtitle="t('pages.subtitle')" subtitle-icon="i-lucide-panels-top-left">
    <template #actions>
      <UButton :label="t('themes.goToForms')" icon="i-lucide-file-text" color="neutral" variant="outline" to="/forms" />
      <UButton :label="t('pages.new')" icon="i-lucide-plus" color="neutral" to="/settings/pages/new" />
    </template>

    <DataView
      id="pages"
      ref="dataView"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="-updated_at"
      default-view="grid"
      :row-actions="rowActions"
      :busy="isBusy"
      :open-row="row => navigateTo(`/settings/pages/${row.id}`)"
      :search-placeholder="t('pages.search')"
      empty-icon="i-lucide-panels-top-left"
      :empty-title="t('pages.emptyTitle')"
      :empty-description="t('pages.emptyDesc')"
    >
      <template #name-cell="{ row }">
        <NuxtLink :to="`/settings/pages/${row.original.id}`" class="flex min-w-0 items-center gap-3 rounded-sm focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
          <span class="w-16 shrink-0 overflow-hidden rounded-sm border border-default"><PageDesignsThumb :tokens="row.original.tokens" /></span>
          <span class="flex min-w-0 flex-col">
            <span class="flex min-w-0 items-center gap-1.5 truncate font-medium text-highlighted">
              <UIcon v-if="isBusy(row.original)" name="i-lucide-loader-circle" class="size-3.5 shrink-0 animate-spin text-muted" />
              {{ name(row.original) }}
            </span>
            <span class="flex items-center gap-1 text-xs text-muted"><UIcon :name="SOURCE_ICON[row.original.source as PageDesign['source']]" class="size-3" />{{ t(`themes.source.${row.original.source}`) }}</span>
          </span>
        </NuxtLink>
      </template>
      <template #style-cell="{ row }">
        <span class="whitespace-nowrap text-default">{{ t(`designer.frame.style.${row.original.tokens.frame.style}`) }} · {{ t(`designer.frame.toneValue.${row.original.tokens.frame.tone}`) }}</span>
      </template>
      <template #forms_count-cell="{ row }">
        <span class="text-default">{{ t('themes.formsCount', { count: row.original.forms_count }, row.original.forms_count) }}</span>
      </template>
      <template #share-cell="{ row }">
        <DataShareBar :value="insights?.forms_total ? row.original.forms_count / insights.forms_total : 0" />
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
        <PageDesignsCard :page="row" :name="name(row)" :actions="rowActions(row)" :busy="isBusy(row)" />
      </template>
    </DataView>
  </AppPanel>
</template>
