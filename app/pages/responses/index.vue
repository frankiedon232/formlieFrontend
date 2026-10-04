<!--
  Responses inbox (F11): every form's responses in one place, for the forms the person may see.
  The period's numbers with sparklines, responses over time, review status and the busiest forms,
  then the list (table or grid) with form, status and channel filters; a response opens in the
  side panel (J / K). Old links `/responses?form={id}` go to that form's Responses page.
-->
<script setup lang="ts">
import type { ResponseInsights, ResponseRow, ResponseStatus } from '#shared/types/responses'

definePageMeta({ breadcrumb: 'nav.responses' })

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const api = useApi()
const { handle } = useErrorHandler()
const { relative } = useFormat()
if (typeof route.query.form === 'string' && route.query.form && !route.query.form.includes(',')) await navigateTo(`/forms/${route.query.form}/responses`, { replace: true })
useHead({ title: () => t('nav.responses') })

const PERIODS = { '7d': 7, '30d': 30, '90d': 90, '12m': 365 } as const
type Period = keyof typeof PERIODS
const period = computed<Period>({
  get: () => (String(route.query.period ?? '') in PERIODS ? (route.query.period as Period) : '30d'),
  set: value => void router.replace({ query: { ...route.query, period: value === '30d' ? undefined : value } }),
})
const periods = computed(() => (Object.keys(PERIODS) as Period[]).map(value => ({ value, label: t(`responses.period.${value}`) })))

const insights = ref<ResponseInsights | null>(null)
const loading = ref(true)
const failed = ref(false)
async function load() {
  loading.value = !insights.value
  failed.value = false
  try {
    const to = new Date().toISOString().slice(0, 10)
    const from = new Date(Date.now() - (PERIODS[period.value] - 1) * 86_400_000).toISOString().slice(0, 10)
    insights.value = (await api.get<ResponseInsights>('/responses/insights', { from, to })).data
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(period, load)

const statusFilter = computed(() => (typeof route.query.status === 'string' && !route.query.status.includes(',') ? route.query.status : null))
const filterStatus = (status: ResponseStatus | null) =>
  void router.replace({ query: { ...route.query, status: status && statusFilter.value !== status ? status : undefined, page: undefined } })

const list = useTemplateRef<{ refresh: () => Promise<void> }>('list')
const openId = ref<string | null>(null)
const ids = ref<string[]>([])
const panel = ref(false)
function openRow(row: ResponseRow, rows: ResponseRow[]) {
  ids.value = rows.map(item => item.id)
  openId.value = row.id
  panel.value = true
}
function openById(id: string) {
  if (!ids.value.includes(id)) ids.value = [id]
  openId.value = id
  panel.value = true
}
let timer: ReturnType<typeof setTimeout> | undefined
function changed() {
  void list.value?.refresh()
  clearTimeout(timer)
  timer = setTimeout(() => void load(), 600)
}
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <AppPanel
    id="responses"
    :title="t('nav.responses')"
    :subtitle="insights?.last_at ? t('responses.subtitle', { when: relative(insights.last_at) }) : t('responses.subtitleNone')"
    subtitle-icon="i-lucide-inbox"
  >
    <template #actions>
      <UTabs v-model="period" :items="periods" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="hidden md:flex" :aria-label="t('responses.period.label')" />
      <USelect v-model="period" :items="periods" class="w-28 md:hidden" :aria-label="t('responses.period.label')" />
    </template>

    <div v-if="loading" class="flex flex-col gap-4" :aria-label="t('common.loading')">
      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><USkeleton v-for="n in 4" :key="n" class="h-32 rounded-lg" /></div>
      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]"><USkeleton class="h-72 rounded-lg" /><USkeleton class="h-72 rounded-lg" /></div>
      <USkeleton class="h-96 rounded-lg" />
    </div>
    <UEmpty
      v-else-if="failed || !insights"
      icon="i-lucide-cloud-alert"
      :title="t('dataView.errorTitle')"
      :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: load }]"
      variant="outline"
    />
    <div v-else class="flex flex-col gap-4">
      <FormsResponsesKpis :insights="insights" @review="filterStatus('new')" />
      <div class="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <FormsResponsesTrend :insights="insights" />
        <FormsResponsesBreakdown :insights="insights" :status="statusFilter" @status="filterStatus" />
      </div>
      <FormsResponsesInbox ref="list" @open="openRow" @changed="changed" />
    </div>

    <FormsResponsesDetail :id="openId" v-model:open="panel" :ids="ids" @go="openById" @changed="changed" />
  </AppPanel>
</template>
