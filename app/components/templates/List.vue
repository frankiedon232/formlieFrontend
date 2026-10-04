<!--
  Template list (F9) used by a category page (Formalie's templates in one category) and by "Your
  templates" (the workspace's own, saved from forms). Locked list format (rule 21): the table with
  Columns and a share-of-use bar, the locked card; a row or card opens the template. Use → name + folder → builder. Owner, 2026-10-03: categories first, Formalie and own
  templates kept apart.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { TemplateSummary } from '#shared/types/templates'
import { TEMPLATE_CATEGORIES, categoryOf } from '#shared/templates/categories'

const props = defineProps<{
  /** DataView id (view switch and filters are remembered per list). */
  id: string
  source: 'system' | 'workspace'
  /** Fixed category (a category page); otherwise a category filter is offered. */
  category?: string
  /** Forms made from any template (top card numbers), for the share of use. */
  total?: number
}>()
const emit = defineEmits<{ changed: [] }>()
const { t } = useI18n()
const templates = useTemplates()
const confirm = useConfirm()
const { number, relative } = useFormat()

const categoryLabel = (key: string) => t(`templates.categories.${key}`)
const filters = computed<DataFilter[]>(() => [
  ...(props.category
    ? []
    : [
        {
          key: 'category',
          label: t('templates.filter.category'),
          icon: 'i-lucide-shapes',
          options: TEMPLATE_CATEGORIES.map(c => ({ value: c.key, label: categoryLabel(c.key), dot: c.dot })),
        },
      ]),
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

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('templates.col.name'), sortable: true, fixed: true },
  ...(props.category
    ? []
    : [{ key: 'category', label: t('templates.col.category'), hideBelow: 'md' as const }]),
  { key: 'fields_count', label: t('templates.col.questions'), sortable: true, hideBelow: 'lg' },
  { key: 'forms_count', label: t('templates.col.forms'), sortable: true, hideBelow: 'sm' },
  { key: 'responses_count', label: t('templates.col.responses'), sortable: true, hideBelow: 'lg' },
  { key: 'share', label: t('templates.card.share'), hideBelow: 'lg', hidden: true },
  { key: 'last_used_at', label: t('templates.col.lastUsed'), sortable: true, hideBelow: 'lg' },
])
const sortOptions = computed(() => [
  { label: t('templates.sort.popular'), value: '-forms_count' },
  { label: t('templates.sort.responses'), value: '-responses_count' },
  { label: t('templates.sort.name'), value: 'name' },
  { label: t('templates.sort.short'), value: 'minutes' },
  { label: t('templates.sort.recent'), value: '-updated_at' },
])
const fetcher: DataFetcher<TemplateSummary> = (params, signal) =>
  templates.list(
    { ...params, source: props.source, ...(props.category ? { category: props.category } : {}) },
    signal,
  )

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
    emit('changed')
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
    {
      label: t('templates.duplicate'),
      icon: 'i-lucide-copy',
      onSelect: () => void act(template, () => templates.duplicate(template)),
    },
  ],
  ...(template.source === 'workspace'
    ? [
        [
          {
            label: t('templates.delete'),
            icon: 'i-lucide-trash-2',
            color: 'error' as const,
            onSelect: () => void remove(template),
          },
        ],
      ]
    : []),
]
const isBusy = (template: TemplateSummary) => busyKeys.value.has(template.key)
const mine = computed(() => props.source === 'workspace')
</script>

<template>
  <DataView
    :id="id"
    ref="dataView"
    :columns="columns"
    :fetcher="fetcher"
    :filters="filters"
    :sort-options="sortOptions"
    :default-sort="mine ? '-updated_at' : '-forms_count'"
    default-view="grid"
    :row-actions="rowActions"
    :busy="isBusy"
    :open-row="row => navigateTo(`/templates/${row.key}`)"
    :search-placeholder="t('templates.search')"
    :empty-icon="mine ? 'i-lucide-bookmark-plus' : 'i-lucide-layout-template'"
    :empty-title="mine ? t('templates.mine.emptyTitle') : t('templates.emptyTitle')"
    :empty-description="mine ? t('templates.mine.emptyDesc') : t('templates.emptyDesc')"
  >
    <template v-if="mine" #empty-actions>
      <UButton
        :label="t('templates.mine.openForms')"
        icon="i-lucide-file-text"
        color="neutral"
        variant="outline"
        to="/forms"
      />
      <UButton
        :label="t('templates.mine.browse')"
        icon="i-lucide-layout-template"
        color="neutral"
        to="/templates"
      />
    </template>
    <template #name-cell="{ row }">
      <NuxtLink
        :to="`/templates/${row.original.key}`"
        class="flex min-w-0 items-center gap-3 rounded-sm focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
      >
        <span class="w-16 shrink-0 overflow-hidden rounded-sm border border-default">
          <TemplatesThumb
            :theme="row.original.theme"
            :title="row.original.name"
            :labels="row.original.preview"
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
            {{ row.original.name }}
          </span>
          <span class="truncate text-xs text-muted">{{
            t('templates.minutes', { n: row.original.minutes })
          }}</span>
        </span>
      </NuxtLink>
    </template>
    <template #category-cell="{ row }">
      <span class="flex items-center gap-1.5">
        <span
          class="size-2 rounded-[1px]"
          :class="categoryOf(row.original.category)?.dot"
          aria-hidden="true"
        />
        {{ categoryLabel(row.original.category) }}
      </span>
    </template>
    <template #forms_count-cell="{ row }">
      <span class="tabular-nums">{{ number(row.original.forms_count) }}</span>
    </template>
    <template #responses_count-cell="{ row }">
      <span class="tabular-nums">{{ number(row.original.responses_count) }}</span>
    </template>
    <template #share-cell="{ row }">
      <DataShareBar :value="total ? row.original.forms_count / total : 0" />
    </template>
    <template #last_used_at-cell="{ row }">
      <span>{{
        row.original.last_used_at ? relative(row.original.last_used_at) : t('templates.neverUsed')
      }}</span>
    </template>
    <template #grid-card="{ row }">
      <TemplatesCard :template="row" :actions="rowActions(row)" :busy="isBusy(row)" :total="total" />
    </template>
  </DataView>

  <TemplatesUseModal v-model:open="useOpen" :template="using" />
</template>
