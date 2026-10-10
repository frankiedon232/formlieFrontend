<!--
  Dashboard → Workspace view (F21 M1): five KPI cards (responses, completion, active forms, to review, needs
  attention) with their change; the activity overview beside the busiest forms and what is coming up; the newest
  responses beside what needs attention and each area at a glance. Loads for the period the page chose.
-->
<script setup lang="ts">
import type { DashboardGroup, WorkspaceDashboard } from '#shared/types/dashboard'

const props = defineProps<{ from: string; to: string; group?: DashboardGroup }>()
const emit = defineEmits<{ loaded: [group: DashboardGroup] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { number } = useFormat()

const data = ref<WorkspaceDashboard | null>(null)
const failed = ref(false)
const recent = useTemplateRef<{ reload: () => Promise<void> }>('recent')
async function load() {
  failed.value = false
  try {
    data.value = (await api.get<WorkspaceDashboard>('/dashboard', { from: props.from, to: props.to, group: props.group })).data
    emit('loaded', data.value.group)
  } catch (error) {
    failed.value = true
    handle(error)
  }
}
watch(() => [props.from, props.to, props.group], load, { immediate: true })
defineExpose({ refresh: () => Promise.all([load(), recent.value?.reload()]) })

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
  <AppEmpty v-if="failed && !data" icon="i-lucide-cloud-off" :title="t('dashboard.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
  <div v-else class="flex flex-col gap-4" :class="data && failed ? 'opacity-60' : ''">
    <div class="flex shrink-0 snap-x gap-3 overflow-x-auto [scrollbar-width:none] sm:grid sm:grid-cols-3 sm:overflow-visible xl:grid-cols-5">
      <ChartsKpi v-for="kpi in kpis" :key="kpi.key" class="min-w-[13.5rem] snap-start sm:min-w-0" :label="kpi.label" :icon="kpi.icon" :value="kpi.value" :change="kpi.change" :hint="kpi.hint" :to="kpi.to" :lower-is-better="kpi.key === 'attention'" />
    </div>
    <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <DashboardActivity :data="data" class="lg:col-span-2" />
      <DashboardSide :data="data" />
    </div>
    <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <DashboardRecent ref="recent" class="lg:col-span-2" />
      <DashboardAttention :data="data" />
    </div>
  </div>
</template>
