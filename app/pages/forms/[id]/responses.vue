<!--
  A form's responses (F11; owner 2026-10-04: "a slim top and the table below"): a thin strip of the
  period's numbers, then Responses (table or grid; the Responses | Insights switch shares the
  toolbar line) or Insights (responses over time, review status / channels / languages, every
  question summarised). A response opens in a side panel (J / K to move). "Responses only" and up.
-->
<script setup lang="ts">
import type { FormSummary } from '#shared/types/forms'
import type { ResponseInsights, ResponseRow, ResponseStatus } from '#shared/types/responses'

definePageMeta({ breadcrumb: 'responses.crumb' })

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const api = useApi()
const { handle } = useErrorHandler()
const { setLabel } = useBreadcrumbs()
const { relative } = useFormat()
const id = String(route.params.id)

const form = ref<FormSummary | null>(null)
const insights = ref<ResponseInsights | null>(null)
const loading = ref(true)
const failed = ref<string | null>(null)
useHead({ title: () => (form.value ? `${form.value.name} · ${t('responses.crumb')}` : t('responses.crumb')) })

// The period for the numbers and charts (the list has its own filters).
const PERIODS = { '7d': 7, '30d': 30, '90d': 90, '12m': 365 } as const
type Period = keyof typeof PERIODS
const period = computed<Period>({
  get: () => (String(route.query.period ?? '') in PERIODS ? (route.query.period as Period) : '30d'),
  set: value => void router.replace({ query: { ...route.query, period: value === '30d' ? undefined : value } }),
})
const periods = computed(() => (Object.keys(PERIODS) as Period[]).map(value => ({ value, label: t(`responses.period.${value}`) })))
const range = () => {
  const to = new Date().toISOString().slice(0, 10)
  return { from: new Date(Date.now() - (PERIODS[period.value] - 1) * 86_400_000).toISOString().slice(0, 10), to }
}

async function loadInsights() {
  insights.value = (await api.get<ResponseInsights>(`/forms/${id}/responses/insights`, range())).data
}
async function load() {
  loading.value = !insights.value
  failed.value = null
  try {
    const [summary] = await Promise.all([api.get<FormSummary>(`/forms/${id}`), loadInsights()])
    form.value = summary.data
    setLabel(`/forms/${id}`, summary.data.name)
  } catch (error) {
    failed.value = handle(error, { silent: true }).code
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(period, () => void loadInsights().catch(handle))

const view = computed<'responses' | 'insights'>({
  get: () => (route.query.view === 'insights' ? 'insights' : 'responses'),
  set: value => void router.replace({ query: { ...route.query, view: value === 'responses' ? undefined : value } }),
})
const statusFilter = computed(() => (typeof route.query.status === 'string' && !route.query.status.includes(',') ? route.query.status : null))
function filterStatus(status: ResponseStatus | null) {
  void router.replace({ query: { ...route.query, view: undefined, status: status && statusFilter.value !== status ? status : undefined, page: undefined } })
}

// The side panel: the rows on screen, J / K through them.
const list = useTemplateRef<{ refresh: () => Promise<void> }>('list')
const openId = ref<string | null>(null)
const ids = ref<string[]>([])
const panel = ref(false)
function openRow(row: ResponseRow, rows: ResponseRow[]) {
  ids.value = rows.map(item => item.id)
  openId.value = row.id
  panel.value = true
}
// A shared link (`?response=`) opens that response.
onMounted(() => typeof route.query.response === 'string' && openById(route.query.response))
function openById(responseId: string) {
  if (!ids.value.includes(responseId)) ids.value = [responseId]
  openId.value = responseId
  panel.value = true
}
let refreshTimer: ReturnType<typeof setTimeout> | undefined
/** After a change: the list now, the numbers a moment later (a few changes in a row = one reload). */
function changed() {
  void list.value?.refresh()
  clearTimeout(refreshTimer)
  refreshTimer = setTimeout(() => void loadInsights().catch(() => undefined), 600)
}
onBeforeUnmount(() => clearTimeout(refreshTimer))
const canEdit = computed(() => canEditForm(form.value))
</script>

<template>
  <AppPanel
    id="form-responses"
    :title="form?.name ?? t('responses.crumb')"
    :subtitle="insights?.last_at ? t('responses.subtitle', { when: relative(insights.last_at) }) : t('responses.subtitleNone')"
    subtitle-icon="i-lucide-inbox"
  >
    <template v-if="form" #actions>
      <UTabs v-model="period" :items="periods" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="hidden md:flex" :aria-label="t('responses.period.label')" />
      <USelect v-model="period" :items="periods" class="w-28 md:hidden" :aria-label="t('responses.period.label')" />
      <UButton :to="`/forms/${id}`" icon="i-lucide-file-text" :label="t('responses.toForm')" color="neutral" variant="outline" class="hidden sm:inline-flex" />
    </template>

    <!-- Loading: mirrors KPI row, chart + side card, tabs + table -->
    <div v-if="loading" class="flex flex-col gap-4" :aria-label="t('common.loading')">
      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><USkeleton v-for="n in 4" :key="n" class="h-32 rounded-lg" /></div>
      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]"><USkeleton class="h-72 rounded-lg" /><USkeleton class="h-72 rounded-lg" /></div>
      <USkeleton class="h-96 rounded-lg" />
    </div>

    <UEmpty
      v-else-if="failed"
      :icon="failed === 'FRM-GEN-1004' ? 'i-lucide-file-question' : 'i-lucide-cloud-alert'"
      :title="failed === 'FRM-GEN-1004' ? t('forms.detail.notFound') : t('dataView.errorTitle')"
      :actions="[
        ...(failed === 'FRM-GEN-1004' ? [] : [{ label: t('common.retry'), color: 'neutral' as const, variant: 'outline' as const, onClick: load }]),
        { label: t('nav.forms'), to: '/forms', color: 'neutral' as const },
      ]"
      variant="outline"
    />

    <div v-else-if="form && insights" class="flex flex-col gap-4">
      <FormsResponsesOverview :insights="insights" per-form :status="statusFilter" @status="filterStatus" @insights="view = 'insights'" />

      <FormsResponsesList v-if="view === 'responses' && insights.schema" ref="list" :form-id="id" :schema="insights.schema" :can-edit="canEdit" :total="insights.total" @open="openRow" @changed="changed">
        <template #start><FormsResponsesViewSwitch v-model="view" /></template>
      </FormsResponsesList>
      <template v-else-if="view === 'insights'">
        <FormsResponsesViewSwitch v-model="view" class="self-start" />
        <div class="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <FormsResponsesTrend :insights="insights" />
          <FormsResponsesBreakdown :insights="insights" :status="statusFilter" @status="filterStatus" />
        </div>
        <FormsResponsesSummary :insights="insights" @open="openById" />
      </template>
    </div>

    <FormsResponsesDetail :id="openId" v-model:open="panel" :ids="ids" @go="openById" @changed="changed" />
  </AppPanel>
</template>
