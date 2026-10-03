<!--
  Templates gallery (F9): a catalogue of ready forms, each in its own design. Category chips
  (with counts) drive the same URL filter as the DataView filter, so the DataView flow stays as it
  is; Grid shows themed cards, Table shows usage numbers. Use → name + folder → builder.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { TemplateFacets, TemplateSummary } from '#shared/types/templates'
import { TEMPLATE_CATEGORIES, categoryOf } from '#shared/templates/categories'

definePageMeta({ breadcrumb: 'nav.templates' })
const { t } = useI18n()
useHead({ title: () => t('nav.templates') })
const route = useRoute()
const router = useRouter()
const templates = useTemplates()
const confirm = useConfirm()
const { number, relative } = useFormat()

// Category counts (system + workspace), loaded in the background.
const facets = ref<TemplateFacets | null>(null)
async function loadFacets() {
  try {
    facets.value = await templates.facets()
  } catch {
    // Chips and filter simply show no counts.
  }
}
onMounted(loadFacets)

const categoryLabel = (key: string) => t(`templates.categories.${key}`)
const filters = reactive<DataFilter[]>([
  {
    key: 'category',
    label: t('templates.filter.category'),
    icon: 'i-lucide-shapes',
    options: TEMPLATE_CATEGORIES.map(c => ({ value: c.key, label: categoryLabel(c.key), dot: c.dot })),
  },
  {
    key: 'source',
    label: t('templates.filter.source'),
    icon: 'i-lucide-library',
    options: [
      { value: 'system', label: t('templates.source.system') },
      { value: 'workspace', label: t('templates.source.workspace') },
    ],
  },
  {
    key: 'features',
    label: t('templates.filter.features'),
    icon: 'i-lucide-sparkle',
    options: [
      { value: 'calculations', label: t('templates.badge.calculations') },
      { value: 'logic', label: t('templates.badge.logic') },
    ],
  },
])
// Counts arrive after the first paint: put them on the filter options as they come.
watch(facets, value => {
  if (!value) return
  for (const option of filters[0]!.options) option.label = `${categoryLabel(option.value)} (${value.categories[option.value] ?? 0})`
})

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('templates.col.name'), sortable: true },
  { key: 'category', label: t('templates.col.category'), hideBelow: 'md' },
  { key: 'fields_count', label: t('templates.col.questions'), sortable: true, hideBelow: 'lg' },
  { key: 'forms_count', label: t('templates.col.forms'), sortable: true, hideBelow: 'sm' },
  { key: 'responses_count', label: t('templates.col.responses'), sortable: true, hideBelow: 'lg' },
  { key: 'last_used_at', label: t('templates.col.lastUsed'), sortable: true, hideBelow: 'lg' },
])
const sortOptions = computed(() => [
  { label: t('templates.sort.popular'), value: '-forms_count' },
  { label: t('templates.sort.responses'), value: '-responses_count' },
  { label: t('templates.sort.name'), value: 'name' },
  { label: t('templates.sort.short'), value: 'minutes' },
  { label: t('templates.sort.recent'), value: '-updated_at' },
])
const fetcher: DataFetcher<TemplateSummary> = (params, signal) => templates.list(params, signal)

// Chips: one category at a time (or all), shared with the filter through the URL. Categories
// without templates yet stay hidden (the catalogue grows in milestones).
const visibleCategories = computed(() =>
  TEMPLATE_CATEGORIES.filter(c => !facets.value || (facets.value.categories[c.key] ?? 0) > 0 || activeCategory.value.includes(c.key)),
)
const activeCategory = computed(() => String(route.query.category ?? '').split(',').filter(Boolean))
function pickCategory(key: string | null) {
  const query = { ...route.query }
  delete query.page
  if (key && !(activeCategory.value.length === 1 && activeCategory.value[0] === key)) query.category = key
  else delete query.category
  router.replace({ query })
}

// Use / duplicate / delete
const using = ref<TemplateSummary | null>(null)
const useOpen = ref(false)
function startUse(template: TemplateSummary) {
  using.value = template
  useOpen.value = true
}
const busyKeys = ref(new Set<string>())
const dataView = useTemplateRef<{ refresh: () => Promise<void> }>('dataView')
async function act(template: TemplateSummary, action: () => Promise<unknown>) {
  busyKeys.value.add(template.key)
  try {
    await action()
    dataView.value?.refresh()
    void loadFacets()
  } finally {
    busyKeys.value.delete(template.key)
  }
}
async function remove(template: TemplateSummary) {
  const ok = await confirm({
    title: t('templates.deleteTitle', { name: template.name }),
    description: t('templates.deleteDesc'),
    danger: true,
    confirmLabel: t('templates.delete'),
  })
  if (ok) await act(template, () => templates.remove(template))
}
const rowActions = (template: TemplateSummary): DropdownMenuItem[][] => [
  [
    { label: t('templates.use'), icon: 'i-lucide-file-plus', onSelect: () => startUse(template) },
    { label: t('templates.open'), icon: 'i-lucide-eye', to: `/templates/${template.key}` },
    { label: t('templates.duplicate'), icon: 'i-lucide-copy', onSelect: () => void act(template, () => templates.duplicate(template)) },
  ],
  ...(template.source === 'workspace'
    ? [[{ label: t('templates.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove(template) }]]
    : []),
]
const isBusy = (template: TemplateSummary) => busyKeys.value.has(template.key)
</script>

<template>
  <AppPanel id="templates" :title="t('nav.templates')" :subtitle="t('templates.subtitle')" subtitle-icon="i-lucide-layout-template">
    <template #actions>
      <UButton :label="t('templates.blank')" icon="i-lucide-file" color="neutral" variant="outline" to="/forms/new" />
    </template>

    <!-- Category chips (horizontal scroll on phones) -->
    <nav :aria-label="t('templates.filter.category')" class="-mx-1 flex shrink-0 gap-1.5 overflow-x-auto px-1 pb-1 sm:flex-wrap sm:overflow-visible">
      <UButton
        :label="t('templates.all')"
        :trailing="false"
        color="neutral"
        :variant="activeCategory.length ? 'outline' : 'solid'"
        size="sm"
        class="shrink-0 rounded-full"
        :aria-pressed="!activeCategory.length"
        @click="pickCategory(null)"
      >
        <template #trailing>
          <span v-if="facets" class="text-xs opacity-70 tabular-nums">{{ number(facets.total) }}</span>
        </template>
      </UButton>
      <UButton
        v-for="category in visibleCategories"
        :key="category.key"
        color="neutral"
        :variant="activeCategory.includes(category.key) ? 'solid' : 'outline'"
        size="sm"
        class="shrink-0 rounded-full"
        :aria-pressed="activeCategory.includes(category.key)"
        @click="pickCategory(category.key)"
      >
        <span class="size-2 rounded-[1px]" :class="category.dot" aria-hidden="true" />
        {{ categoryLabel(category.key) }}
        <span v-if="facets" class="text-xs opacity-70 tabular-nums">{{ number(facets.categories[category.key] ?? 0) }}</span>
      </UButton>
    </nav>

    <DataView
      id="templates"
      ref="dataView"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="-forms_count"
      default-view="grid"
      :row-actions="rowActions"
      :busy="isBusy"
      :search-placeholder="t('templates.search')"
      empty-icon="i-lucide-layout-template"
      :empty-title="t('templates.emptyTitle')"
      :empty-description="t('templates.emptyDesc')"
    >
      <template #name-cell="{ row }">
        <NuxtLink :to="`/templates/${row.original.key}`" class="flex min-w-0 items-center gap-3 rounded-sm focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
          <span class="w-16 shrink-0 overflow-hidden rounded-sm border border-default">
            <TemplatesThumb :theme="row.original.theme" :title="row.original.name" :labels="row.original.preview" mini />
          </span>
          <span class="flex min-w-0 flex-col">
            <span class="flex min-w-0 items-center gap-1.5 truncate font-medium text-highlighted">
              <UIcon v-if="isBusy(row.original)" name="i-lucide-loader-circle" class="size-3.5 shrink-0 animate-spin text-muted" />
              {{ row.original.name }}
            </span>
            <span class="truncate text-xs text-muted">{{ t('templates.minutes', { n: row.original.minutes }) }}</span>
          </span>
        </NuxtLink>
      </template>
      <template #category-cell="{ row }">
        <span class="flex items-center gap-1.5 text-muted">
          <span class="size-2 rounded-[1px]" :class="categoryOf(row.original.category)?.dot" aria-hidden="true" />
          {{ categoryLabel(row.original.category) }}
        </span>
      </template>
      <template #forms_count-cell="{ row }">
        <span class="tabular-nums">{{ number(row.original.forms_count) }}</span>
      </template>
      <template #responses_count-cell="{ row }">
        <span class="text-muted tabular-nums">{{ number(row.original.responses_count) }}</span>
      </template>
      <template #last_used_at-cell="{ row }">
        <span class="text-muted">{{ row.original.last_used_at ? relative(row.original.last_used_at) : t('templates.neverUsed') }}</span>
      </template>
      <template #grid-card="{ row }">
        <TemplatesCard :template="row" :busy="isBusy(row)" @use="startUse" />
      </template>
    </DataView>

    <TemplatesUseModal v-model:open="useOpen" :template="using" />
  </AppPanel>
</template>
