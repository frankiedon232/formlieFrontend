<!--
  Responses (F11; owner 2026-10-04: grouped by form, responses only inside a form). Two chart cards
  for all forms on top (a review status filters the forms to those with such responses), then
  every form with responses as table or grid (rule 21); a form opens its own Responses page.
  Insights (responses over time, review status, busiest forms) share the toolbar line's switch.
  Sidebar New / Reviewed… arrive as `?review=`; old links `/responses?form={id}` go to that form.
-->
<script setup lang="ts">
import type { ResponseInsights, ResponseStatus } from '#shared/types/responses'

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

const view = computed<'responses' | 'insights'>({
  get: () => (route.query.view === 'insights' ? 'insights' : 'responses'),
  set: value => void router.replace({ query: { ...route.query, view: value === 'responses' ? undefined : value } }),
})
/** One review status at a time: the forms that have such responses (the sidebar uses the same). */
const review = computed(() => (typeof route.query.review === 'string' && !route.query.review.includes(',') ? route.query.review : null))
const filterReview = (status: ResponseStatus) =>
  void router.replace({ query: { ...route.query, view: undefined, review: review.value === status ? undefined : status, page: undefined } })
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
      <div class="grid gap-4 lg:grid-cols-2"><USkeleton v-for="n in 2" :key="n" class="h-40 rounded-lg" /></div>
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"><USkeleton v-for="n in 6" :key="n" class="h-64 rounded-lg" /></div>
    </div>
    <UEmpty
      v-else-if="failed || !insights"
      icon="i-lucide-cloud-alert"
      :title="t('dataView.errorTitle')"
      :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: load }]"
      variant="outline"
    />
    <div v-else class="flex flex-col gap-4">
      <FormsResponsesOverview :insights="insights" :status="review" @status="filterReview" @insights="view = 'insights'" />
      <FormsResponsesByForm v-if="view === 'responses'">
        <template #start><FormsResponsesViewSwitch v-model="view" /></template>
      </FormsResponsesByForm>
      <template v-else>
        <FormsResponsesViewSwitch v-model="view" class="self-start" />
        <div class="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <FormsResponsesTrend :insights="insights" />
          <FormsResponsesBreakdown :insights="insights" :status="review" @status="filterReview" />
        </div>
      </template>
    </div>
  </AppPanel>
</template>
