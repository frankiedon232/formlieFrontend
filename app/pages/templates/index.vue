<!--
  Templates (F9), Formalie's categories first (owner, 2026-10-03: 84 templates at once is too
  much). Each category shows how many templates it holds and how they're used; opening one lists
  its templates. The workspace's own templates live apart, under "Your templates". Locked list
  format (rule 21): two chart cards on top, the table with Columns, the locked card; a row opens it.
-->
<script setup lang="ts">
import type { TemplateCategorySummary } from '#shared/types/templates'
import { categoryOf } from '#shared/templates/categories'

definePageMeta({ breadcrumb: 'nav.templates' })
const { t } = useI18n()
useHead({ title: () => t('nav.templates') })
const templates = useTemplates()
const counts = useNavCounts()
const { number, relative } = useFormat()

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('templates.col.category'), sortable: true, fixed: true },
  { key: 'templates_count', label: t('templates.col.templates'), sortable: true },
  { key: 'calculations_count', label: t('templates.badge.calculations'), sortable: true, hideBelow: 'lg' },
  { key: 'forms_count', label: t('templates.col.forms'), sortable: true, hideBelow: 'sm' },
  { key: 'responses_count', label: t('templates.col.responses'), sortable: true, hideBelow: 'lg' },
  { key: 'share', label: t('templates.card.share'), hideBelow: 'lg' },
  { key: 'last_used_at', label: t('templates.col.lastUsed'), sortable: true, hideBelow: 'md' },
])
const sortOptions = computed(() => [
  { label: t('templates.sort.popular'), value: '-forms_count' },
  { label: t('templates.sort.largest'), value: '-templates_count' },
  { label: t('templates.sort.responses'), value: '-responses_count' },
  { label: t('templates.sort.name'), value: 'name' },
])
const { insights } = useTemplateInsights()
const fetcher: DataFetcher<TemplateCategorySummary> = (params, signal) => templates.categories(params, signal)
const rowActions = (category: TemplateCategorySummary) => [
  [
    {
      label: t('templates.categoryCard.browse'),
      icon: 'i-lucide-arrow-right',
      to: `/templates/category/${category.key}`,
    },
  ],
]
</script>

<template>
  <AppPanel
    id="templates"
    :title="t('nav.templates')"
    :subtitle="t('templates.subtitle')"
    subtitle-icon="i-lucide-layout-template"
  >
    <template #actions>
      <UButton
        :label="t('nav.templatesMine')"
        icon="i-lucide-bookmark"
        color="neutral"
        variant="outline"
        to="/templates/mine"
      >
        <template v-if="counts.counts.value?.templates.mine" #trailing>
          <UBadge
            :label="number(counts.counts.value.templates.mine)"
            color="neutral"
            variant="soft"
            size="sm"
            class="tabular-nums"
          />
        </template>
      </UButton>
      <UButton :label="t('templates.blank')" icon="i-lucide-file" color="neutral" to="/forms/new" />
    </template>

    <div class="flex flex-col gap-4">
      <TemplatesOverview :insights="insights" />
      <DataView
        id="template-categories"
        :columns="columns"
        :fetcher="fetcher"
        :sort-options="sortOptions"
        default-sort="-forms_count"
        default-view="grid"
        :row-actions="rowActions"
        :open-row="row => navigateTo(`/templates/category/${row.key}`)"
        :search-placeholder="t('templates.searchCategories')"
        empty-icon="i-lucide-shapes"
        :empty-title="t('templates.emptyTitle')"
        :empty-description="t('templates.emptyDesc')"
      >
        <template #name-cell="{ row }">
          <NuxtLink
            :to="`/templates/category/${row.original.key}`"
            class="flex min-w-0 items-center gap-3 rounded-sm focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
          >
            <span class="w-16 shrink-0 overflow-hidden rounded-sm border border-default">
              <TemplatesThumb
                :theme="row.original.theme"
                :title="row.original.name"
                :labels="row.original.examples"
                mini
              />
            </span>
            <span class="flex min-w-0 flex-col">
              <span class="flex min-w-0 items-center gap-1.5 truncate font-medium text-highlighted">
                <span
                  class="size-2 shrink-0 rounded-[1px]"
                  :class="categoryOf(row.original.key)?.dot"
                  aria-hidden="true"
                />
                {{ row.original.name }}
              </span>
              <span class="truncate text-xs text-muted">{{ row.original.examples.join(' · ') }}</span>
            </span>
          </NuxtLink>
        </template>
        <template #templates_count-cell="{ row }">
          <span class="tabular-nums">{{ number(row.original.templates_count) }}</span>
        </template>
        <template #calculations_count-cell="{ row }">
          <span class="tabular-nums">{{ number(row.original.calculations_count) }}</span>
        </template>
        <template #forms_count-cell="{ row }">
          <span class="tabular-nums">{{ number(row.original.forms_count) }}</span>
        </template>
        <template #responses_count-cell="{ row }">
          <span class="tabular-nums">{{ number(row.original.responses_count) }}</span>
        </template>
        <template #share-cell="{ row }">
          <DataShareBar
            :value="insights?.forms_total ? row.original.forms_count / insights.forms_total : 0"
          />
        </template>
        <template #last_used_at-cell="{ row }">
          <span>{{
            row.original.last_used_at ? relative(row.original.last_used_at) : t('templates.neverUsed')
          }}</span>
        </template>
        <template #grid-card="{ row }">
          <TemplatesCategoryCard :category="row" :actions="rowActions(row)" :total="insights?.forms_total" />
        </template>
      </DataView>
    </div>
  </AppPanel>
</template>
