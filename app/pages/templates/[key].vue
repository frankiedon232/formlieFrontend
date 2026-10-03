<!--
  Template page (F9): live preview in the template's design, what's included (calculations with
  their formulas), usage, and every form made from it. Use → name + folder → builder.
-->
<script setup lang="ts">
import type { FormSummary } from '#shared/types/forms'
import type { TemplateDetail } from '#shared/types/templates'

definePageMeta({ breadcrumb: 'nav.templates' })
const { t } = useI18n()
const route = useRoute()
const api = useApi()
const templates = useTemplates()
const { setLabel } = useBreadcrumbs()
const { relative, number } = useFormat()
const { handle } = useErrorHandler()

const key = computed(() => String(route.params.key ?? ''))
const template = ref<TemplateDetail | null>(null)
const loading = ref(true)
const notFound = ref(false)
async function load() {
  loading.value = true
  notFound.value = false
  try {
    template.value = await templates.get(key.value)
    setLabel(route.path, template.value.name)
  } catch (error) {
    template.value = null
    notFound.value = true
    handle(error, { silent: true })
  } finally {
    loading.value = false
  }
}
watch(key, load, { immediate: true })
useHead({ title: () => template.value?.name ?? t('nav.templates') })

const useOpen = ref(false)
const { busy: duplicating, run } = useBusy()
async function duplicate() {
  if (!template.value) return
  const copy = await run(() => templates.duplicate(template.value!))
  if (copy) await navigateTo(`/templates/${copy.key}`)
}

// Forms made from this template (same columns as the forms list, filtered by template).
const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('forms.col.name'), sortable: true },
  { key: 'status', label: t('forms.col.status') },
  { key: 'responses_count', label: t('forms.col.responses'), sortable: true, hideBelow: 'sm' },
  { key: 'updated_at', label: t('forms.col.updated'), sortable: true, hideBelow: 'md' },
])
const fetcher: DataFetcher<FormSummary> = (params, signal) =>
  api.list<FormSummary>('/forms', { ...params, 'filter[template]': key.value }, { signal })
</script>

<template>
  <AppPanel
    id="template"
    :title="template?.name ?? t('nav.templates')"
    :subtitle="template ? `${t(`templates.categories.${template.category}`)} · ${t('templates.minutes', { n: template.minutes })}` : undefined"
    :subtitle-icon="template?.icon"
  >
    <template v-if="template" #actions>
      <UButton :label="t('templates.duplicate')" icon="i-lucide-copy" color="neutral" variant="outline" :loading="duplicating" @click="duplicate" />
      <UButton :label="t('templates.use')" icon="i-lucide-file-plus" color="neutral" @click="useOpen = true" />
    </template>

    <!-- Loading: mirrors preview + side panel -->
    <div v-if="loading" class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <USkeleton class="h-[70vh] min-h-96 w-full rounded-lg" />
      <div class="flex flex-col gap-3">
        <USkeleton class="h-48 w-full rounded-lg" />
        <USkeleton class="h-28 w-full rounded-lg" />
      </div>
    </div>

    <UEmpty
      v-else-if="notFound"
      icon="i-lucide-layout-template"
      :title="t('templates.notFound')"
      :description="t('templates.notFoundDesc')"
      :actions="[{ label: t('templates.backToGallery'), icon: 'i-lucide-arrow-left', to: '/templates', color: 'neutral', variant: 'subtle' }]"
      class="my-auto"
    />

    <template v-else-if="template">
      <p class="-mb-2 max-w-3xl text-sm text-muted">{{ template.description }}</p>
      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <TemplatesPreview :schema="template.schema" :title="template.name" />
        <TemplatesIncluded :template="template" />
      </div>

      <section class="flex flex-col gap-3">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('templates.formsFrom', { count: template.forms_count }, template.forms_count) }}</h2>
        <DataView
          :id="`template-forms`"
          :columns="columns"
          :fetcher="fetcher"
          default-sort="-updated_at"
          :search-placeholder="t('forms.searchPlaceholder')"
          empty-icon="i-lucide-file-text"
          :empty-title="t('templates.noFormsTitle')"
          :empty-description="t('templates.noFormsDesc')"
        >
          <template #name-cell="{ row }">
            <NuxtLink :to="`/forms/${row.original.id}`" class="font-medium text-highlighted hover:underline">{{ row.original.name }}</NuxtLink>
          </template>
          <template #status-cell="{ row }">
            <DataStatusBadge :status="row.original.status" />
          </template>
          <template #responses_count-cell="{ row }">
            <span class="tabular-nums">{{ number(row.original.responses_count) }}</span>
          </template>
          <template #updated_at-cell="{ row }">
            <span class="text-muted">{{ relative(row.original.updated_at) }}</span>
          </template>
          <template #grid-card="{ row }">
            <NuxtLink :to="`/forms/${row.id}`" class="flex h-full flex-col gap-2 rounded-lg border border-default p-3 hover:border-accented">
              <span class="font-medium text-highlighted">{{ row.name }}</span>
              <DataStatusBadge :status="row.status" class="self-start" />
              <span class="mt-auto text-xs text-muted">{{ t('forms.col.responses') }}: {{ number(row.responses_count) }} · {{ relative(row.updated_at) }}</span>
            </NuxtLink>
          </template>
        </DataView>
      </section>

      <TemplatesUseModal v-model:open="useOpen" :template="template" />
    </template>
  </AppPanel>
</template>
