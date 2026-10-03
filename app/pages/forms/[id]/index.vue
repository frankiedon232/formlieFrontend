<!--
  Form overview — the form's home: headline numbers, the 30-day response trend, sharing links,
  what the form is made of (each part linked to Build / Logic / Design / Versions), details with
  the template it came from, and its activity. Lifecycle actions and Edit live in the header.
-->
<script setup lang="ts">
import type { FormOverview, FormSummary } from '#shared/types/forms'

const { t } = useI18n()
const route = useRoute()
const api = useApi()
const { setLabel } = useBreadcrumbs()
const { relative } = useFormat()
const { handle } = useErrorHandler()

const form = ref<(FormSummary & { template_key: string | null }) | null>(null)
const overview = ref<FormOverview | null>(null)
const loading = ref(true)
const notFound = ref(false)
useHead({ title: () => form.value?.name ?? t('nav.forms') })

async function load() {
  try {
    const [summary, stats] = await Promise.all([
      api.get<FormSummary & { template_key: string | null }>(`/forms/${route.params.id}`),
      api.get<FormOverview>(`/forms/${route.params.id}/overview`),
    ])
    form.value = summary.data
    overview.value = stats.data
    setLabel(route.path, form.value.name)
  } catch (error) {
    const normalised = handle(error, { silent: true })
    if (normalised.code === 'FRM-GEN-1004') notFound.value = true
    else handle(error)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const actions = useFormActions(load)
const busy = computed(() => !!form.value && actions.isBusy(form.value))
const templateOpen = ref(false)
const availabilityOpen = ref(false)
const menu = useFormMenu(actions, {
  rename: () => {},
  move: () => {},
  tags: () => {},
  saveTemplate: () => (templateOpen.value = true),
  availability: () => (availabilityOpen.value = true),
})
// Header menu: save as template + lifecycle + delete (rename / move / tags live in the list).
const lifecycleItems = computed(() => {
  if (!form.value) return []
  if (form.value.deleted_at)
    return [[{ label: t('forms.actions.restore'), icon: 'i-lucide-undo-2', onSelect: () => actions.lifecycle(form.value!, 'restore') }]]
  return [
    [{ label: t('templates.saveAs'), icon: 'i-lucide-layout-template', onSelect: () => (templateOpen.value = true) }],
    ...menu(form.value).slice(2),
  ]
})
const canSeeActivity = computed(() => useSession().user.value?.role !== 'member')
const subtitle = computed(() =>
  form.value ? t('forms.overview.subtitle', { status: t(`status.${form.value.status}`), updated: relative(form.value.updated_at) }) : undefined,
)
</script>

<template>
  <AppPanel id="form-overview" :title="form?.name ?? t('nav.forms')" :subtitle="subtitle" subtitle-icon="i-lucide-file-text">
    <template v-if="form" #actions>
      <UDropdownMenu :items="lifecycleItems" :content="{ align: 'end' }">
        <UButton icon="i-lucide-ellipsis" :label="t('dataView.actions')" color="neutral" variant="outline" :loading="busy" />
      </UDropdownMenu>
      <UButton
        icon="i-lucide-inbox"
        :label="t('forms.viewResponses')"
        color="neutral"
        variant="outline"
        :to="`/responses?form=${form.id}`"
        class="hidden sm:inline-flex"
      />
      <UButton icon="i-lucide-pencil-ruler" :label="t('forms.detail.edit')" color="neutral" :to="`/forms/${form.id}/build`" :disabled="!!form.deleted_at" />
    </template>

    <!-- Loading: mirrors KPI row, chart + side column -->
    <div v-if="loading" class="flex flex-col gap-4" :aria-label="t('common.loading')">
      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <USkeleton v-for="n in 4" :key="n" class="h-28 w-full rounded-lg" />
      </div>
      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div class="flex flex-col gap-4">
          <USkeleton class="h-64 w-full rounded-lg" />
          <USkeleton class="h-56 w-full rounded-lg" />
        </div>
        <div class="flex flex-col gap-4">
          <USkeleton class="h-72 w-full rounded-lg" />
          <USkeleton class="h-64 w-full rounded-lg" />
        </div>
      </div>
    </div>

    <UEmpty
      v-else-if="notFound"
      icon="i-lucide-file-question"
      :title="t('forms.detail.notFound')"
      :description="t('forms.detail.notFoundDesc')"
      :actions="[{ label: t('nav.forms'), to: '/forms', color: 'neutral', icon: 'i-lucide-arrow-left' }]"
      variant="outline"
    />

    <div
      v-else-if="form && overview"
      class="flex flex-col gap-4"
      :class="busy ? 'pointer-events-none opacity-60' : ''"
      :aria-busy="busy || undefined"
    >
      <UAlert
        v-if="form.deleted_at"
        icon="i-lucide-trash-2"
        color="warning"
        variant="subtle"
        :title="t('forms.detail.inTrash')"
        :actions="[{ label: t('forms.trash.title'), to: '/forms/trash', color: 'neutral', variant: 'outline' }]"
      />

      <FormsOverviewKpis :form-id="form.id" :stats="overview.stats" :daily="overview.daily" />

      <div class="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div class="flex min-w-0 flex-col gap-4">
          <FormsOverviewTrend :days="overview.daily" />
          <FormsOverviewStructure :form="form" :overview="overview" />
        </div>
        <div class="flex min-w-0 flex-col gap-4">
          <FormsOverviewShare :form="form" :accent="(overview.theme.colors as { primary?: string } | undefined)?.primary" />
          <FormsOverviewDetails :form="form" :template="overview.template" @availability="availabilityOpen = true" />
          <UCard v-if="canSeeActivity" variant="outline" :ui="{ body: 'p-4 sm:p-5' }">
            <h2 class="mb-4 text-sm font-semibold text-highlighted">{{ t('forms.detail.activity') }}</h2>
            <AuditTimeline
              :key="form.row_version"
              :filters="{ 'filter[resource_id]': form.id }"
              :limit="6"
              :view-all="`/audit?q=${encodeURIComponent(form.name)}`"
            />
          </UCard>
        </div>
      </div>
    </div>
    <TemplatesSaveModal v-model:open="templateOpen" :form="form" />
    <FormsListAvailabilityModal v-model:open="availabilityOpen" :form="form" @saved="load" />
  </AppPanel>
</template>
