<!--
  Dashboard (F21 M1, design reference 2: docs/design/Screenshot 2026-10-02 092034.png): the workspace home. Header:
  the period (last 30 days by default, kept in the address) and Daily / Weekly / Monthly / Yearly, with New form.
  Five KPI cards (responses, completion, active forms, to review, needs attention) with their change; the activity
  overview beside the busiest forms and what is coming up; then the newest responses beside what needs attention
  and each area at a glance. Everything follows the person's role and folder access.
-->
<script setup lang="ts">
import { DASHBOARD_GROUPS, type DashboardGroup, type WorkspaceDashboard } from '#shared/types/dashboard'

definePageMeta({ breadcrumb: 'nav.dashboard' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const { handle } = useErrorHandler()
const { number } = useFormat()
const { can } = useCan()
useHead({ title: () => t('nav.dashboard') })

// The period and grouping (kept in the address so a link shows the same)
const iso = (time: number) => new Date(time).toISOString().slice(0, 10)
const from = computed(() => (typeof route.query.from === 'string' && route.query.from ? route.query.from : iso(Date.now() - 29 * 86_400_000)))
const to = computed(() => (typeof route.query.to === 'string' && route.query.to ? route.query.to : iso(Date.now())))
const group = computed<DashboardGroup | undefined>(() => (DASHBOARD_GROUPS.includes(route.query.group as DashboardGroup) ? (route.query.group as DashboardGroup) : undefined))
const setPeriod = (start: string, end: string) => void router.replace({ query: { ...route.query, from: start || undefined, to: end || undefined } })
const groups = computed(() => DASHBOARD_GROUPS.map(value => ({ value, label: t(`dashboard.group.${value}`) })))
const chosenGroup = computed({
  get: () => data.value?.group ?? group.value ?? 'day',
  set: value => void router.replace({ query: { ...route.query, group: value } }),
})

const data = ref<WorkspaceDashboard | null>(null)
const failed = ref(false)
const loadedAt = ref<number | null>(null)
const recent = useTemplateRef<{ reload: () => Promise<void> }>('recent')
async function load() {
  failed.value = false
  try {
    data.value = (await api.get<WorkspaceDashboard>('/dashboard', { from: from.value, to: to.value, group: group.value })).data
    loadedAt.value = Date.now()
  } catch (error) {
    failed.value = true
    handle(error)
  }
}
watch([from, to, group], load, { immediate: true })
const refresh = () => Promise.all([load(), recent.value?.reload()])

const change = (kpi: { value: number; previous: number | null } | undefined) => (kpi && kpi.previous ? Math.round(((kpi.value - kpi.previous) / kpi.previous) * 100) : null)
const kpis = computed(() => {
  const k = data.value?.kpis
  return [
    { key: 'responses', icon: 'i-lucide-inbox', label: t('dashboard.kpi.responses'), value: k ? number(k.responses.value) : null, change: change(k?.responses), to: '/responses' },
    { key: 'completion', icon: 'i-lucide-percent', label: t('dashboard.kpi.completion'), value: k ? `${number(k.completion_rate.value, { maximumFractionDigits: 1 })}%` : null, change: k && k.completion_rate.previous !== null ? Math.round((k.completion_rate.value - k.completion_rate.previous) * 10) / 10 : null, to: '/analytics' },
    { key: 'active', icon: 'i-lucide-file-check-2', label: t('dashboard.kpi.active'), value: k ? number(k.active_forms.value) : null, change: change(k?.active_forms), to: '/forms?status=published' },
    { key: 'review', icon: 'i-lucide-list-checks', label: t('dashboard.kpi.review'), value: k ? number(k.to_review.value) : null, change: null, to: '/responses?review=new', hint: t('dashboard.kpi.reviewHint') },
    { key: 'attention', icon: 'i-lucide-triangle-alert', label: t('dashboard.kpi.attention'), value: k ? number(k.attention.value) : null, change: null, to: '#attention', hint: k?.attention.value ? t('dashboard.kpi.attentionHint') : t('dashboard.kpi.allGood') },
  ]
})
</script>

<template>
  <AppPanel id="dashboard" :title="t('nav.dashboard')" :subtitle="loadedAt ? t('dashboard.synced') : t('dashboard.subtitle')" subtitle-icon="i-lucide-refresh-cw">
    <template #actions>
      <UButton icon="i-lucide-refresh-cw" color="neutral" variant="ghost" square :aria-label="t('dashboard.refresh')" class="max-xl:hidden" @click="refresh" />
      <DataDateRangePicker :from="from" :to="to" @change="setPeriod" />
      <UTabs v-model="chosenGroup" :items="groups" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" class="max-2xl:hidden" :aria-label="t('dashboard.groupLabel')" />
      <UButton v-if="can('forms.create')" :label="t('dashboard.newForm')" icon="i-lucide-plus" color="neutral" to="/forms/new" />
    </template>

    <AppEmpty v-if="failed && !data" icon="i-lucide-cloud-off" :title="t('dashboard.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
    <div v-else class="flex flex-col gap-4" :class="data && failed ? 'opacity-60' : ''">
      <div class="flex shrink-0 snap-x gap-3 overflow-x-auto [scrollbar-width:none] sm:grid sm:grid-cols-3 sm:overflow-visible xl:grid-cols-5">
        <ChartsKpi v-for="kpi in kpis" :key="kpi.key" class="min-w-[13.5rem] snap-start sm:min-w-0" :label="kpi.label" :icon="kpi.icon" :value="kpi.value" :change="kpi.change" :hint="kpi.hint" :to="kpi.to" :lower-is-better="kpi.key === 'attention'" />
      </div>
      <UTabs v-model="chosenGroup" :items="groups" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" class="self-end 2xl:hidden" :aria-label="t('dashboard.groupLabel')" />
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <DashboardActivity :data="data" class="lg:col-span-2" />
        <DashboardSide :data="data" />
      </div>
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <DashboardRecent ref="recent" class="lg:col-span-2" />
        <DashboardAttention :data="data" />
      </div>
    </div>
  </AppPanel>
</template>
