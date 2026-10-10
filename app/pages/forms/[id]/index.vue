<!--
  Form overview, the form's home (rule 21, owner 2026-10-04): two chart cards on top (responses of
  the last 30 days with daily bars; review status as thin lines, a status opens the filtered
  responses), the latest responses as cards (each opens its response), highlights of the most
  telling questions, what the form is made of; on the side sharing, details and activity.
  Lifecycle actions and Edit live in the header.
-->
<script setup lang="ts">
import type { FormOverview, FormSummary } from '#shared/types/forms'
import type { ResponseInsights } from '#shared/types/responses'

const { t } = useI18n()
const route = useRoute()
const api = useApi()
const { setLabel } = useBreadcrumbs()
const { relative } = useFormat()
const { handle } = useErrorHandler()

const form = ref<(FormSummary & { template_key: string | null }) | null>(null)
const overview = ref<FormOverview | null>(null)
const insights = ref<ResponseInsights | null>(null)
const loading = ref(true)
const notFound = ref(false)
useHead({ title: () => form.value?.name ?? t('nav.forms') })

async function load() {
  try {
    const to = new Date().toISOString().slice(0, 10)
    const from = new Date(Date.now() - 29 * 86_400_000).toISOString().slice(0, 10)
    const [summary, stats, numbers] = await Promise.all([
      api.get<FormSummary & { template_key: string | null }>(`/forms/${route.params.id}`),
      api.get<FormOverview>(`/forms/${route.params.id}/overview`),
      api.get<ResponseInsights>(`/forms/${route.params.id}/responses/insights`, { from, to }),
    ])
    form.value = summary.data
    overview.value = stats.data
    insights.value = numbers.data
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
/** Each button follows what this person may do with this form (F22 R2: role scope, maker, sharing, folder). */
const editable = computed(() => canEditForm(form.value))
const allowed = (action: Parameters<typeof formCan>[1]) => formCan(form.value, action)
// Header menu: duplicate, availability, share, save as template, lifecycle, delete (rename / move / tags live in the list).
const lifecycleItems = computed(() => (form.value ? menu(form.value, { page: true }) : []))
const canSeeActivity = computed(() => useCan().can('audit.view'))
const subtitle = computed(() =>
  form.value ? t('forms.overview.subtitle', { status: t(`status.${form.value.status}`), updated: relative(form.value.updated_at) }) : undefined,
)
</script>

<template>
  <AppPanel id="form-overview" :title="form?.name ?? t('nav.forms')" :subtitle="subtitle" subtitle-icon="i-lucide-file-text">
    <template v-if="form" #actions>
      <UDropdownMenu v-if="lifecycleItems.length" :items="lifecycleItems" :content="{ align: 'end' }">
        <UButton icon="i-lucide-ellipsis" :label="t('dataView.actions')" color="neutral" variant="outline" :loading="busy" />
      </UDropdownMenu>
      <UButton
        v-if="form.responses_can?.view"
        icon="i-lucide-inbox"
        :label="t('forms.viewResponses')"
        color="neutral"
        variant="outline"
        :to="`/forms/${form.id}/responses`"
        class="hidden sm:inline-flex"
      />
      <!-- People access: only editors open the editor; "Can view" gets the read-only preview page. -->
      <UButton
        v-if="allowed('preview')"
        icon="i-lucide-eye"
        :label="t('preview.crumb')"
        color="neutral"
        :variant="editable ? 'outline' : 'solid'"
        :to="`/forms/${form.id}/preview`"
        :disabled="!!form.deleted_at"
        :class="editable ? 'hidden sm:inline-flex' : ''"
      />
      <UButton v-if="editable" icon="i-lucide-pencil-ruler" :label="t('forms.detail.edit')" color="neutral" :to="`/forms/${form.id}/build`" :disabled="!!form.deleted_at" />
    </template>

    <!-- Loading: mirrors KPI row, chart + side column -->
    <div v-if="loading" class="flex flex-col gap-4" :aria-label="t('common.loading')">
      <div class="grid gap-4 lg:grid-cols-2">
        <USkeleton v-for="n in 2" :key="n" class="h-40 w-full rounded-lg" />
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

    <AppEmpty
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

      <FormsResponsesOverview
        v-if="insights"
        :insights="insights"
        per-form
        @status="status => navigateTo(`/forms/${form!.id}/responses?status=${status}`)"
        @insights="navigateTo(`/forms/${form!.id}/responses?view=insights`)"
      />

      <div class="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div class="flex min-w-0 flex-col gap-4">
          <FormsOverviewLatest :form-id="form.id" :schema="insights?.schema ?? null" :published="form.status !== 'draft'" />
          <FormsOverviewHighlights v-if="insights" :form-id="form.id" :insights="insights" />
          <FormsOverviewStructure :form="form" :overview="overview" :read-only="!editable" :can-versions="allowed('versions')" />
        </div>
        <div class="flex min-w-0 flex-col gap-4">
          <FormsOverviewShare :form="form" :read-only="!allowed('share_view')" :accent="(overview.theme.colors as { primary?: string } | undefined)?.primary" />
          <FormsOverviewDetails :form="form" :template="overview.template" :read-only="!allowed('availability')" @availability="availabilityOpen = true" />
          <FormsOverviewStorage :form-id="form.id" />
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
    <template v-if="form">
      <TemplatesSaveModal v-if="allowed('save_template')" v-model:open="templateOpen" :form="form" />
      <FormsListAvailabilityModal v-if="allowed('availability')" v-model:open="availabilityOpen" :form="form" @saved="load" />
    </template>
  </AppPanel>
</template>
