<!--
  AI assistant → Response analysis (F19 M4): pick a form and a period, the assistant reads its responses
  (themes and tone in written answers, ratings and choices against the period before, what stands out),
  then ask it questions in plain words. Form and period live in the address (?form, ?from, ?to).
-->
<script setup lang="ts">
import type { AiAnalysis } from '#shared/types/ai'
import { AI_KIND_META } from '#shared/utils/ai/kinds'

definePageMeta({ breadcrumb: 'nav.aiAnalysis' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const { handle } = useErrorHandler()
const { can } = useCan()
const ai = useAi()
useHead({ title: () => t('nav.aiAnalysis') })
onMounted(() => void ai.load())

const iso = (ms: number) => new Date(ms).toISOString().slice(0, 10)
const formId = computed({
  get: () => (typeof route.query.form === 'string' ? route.query.form : undefined),
  set: value => void router.replace({ query: { ...route.query, form: value } }),
})
const from = computed(() => (typeof route.query.from === 'string' && route.query.from ? route.query.from : iso(Date.now() - 29 * 86_400_000)))
const to = computed(() => (typeof route.query.to === 'string' && route.query.to ? route.query.to : iso(Date.now())))
const setPeriod = (start: string, end: string) => void router.replace({ query: { ...route.query, from: start || undefined, to: end || undefined } })

const analysis = ref<AiAnalysis | null>(null)
const busy = ref(false)
const failed = ref(false)
async function run() {
  if (!formId.value || busy.value) return
  busy.value = true
  failed.value = false
  try {
    analysis.value = (await api.post<AiAnalysis>('/ai/analysis', { form_id: formId.value, from: from.value, to: to.value })).data
  } catch (error) {
    failed.value = true
    handle(error)
  } finally {
    busy.value = false
  }
}
// A new form or period shows the old result dimmed until asked again
const stale = computed(() => !!analysis.value && (analysis.value.form.id !== formId.value || analysis.value.period.from !== from.value || analysis.value.period.to !== to.value))
const steps = computed(() => [t('ai.analysis.step.read'), t('ai.analysis.step.themes'), t('ai.analysis.step.compare')])
</script>

<template>
  <AppPanel id="ai-analysis" :title="t('nav.aiAnalysis')" :subtitle="t('ai.section.analysis')" subtitle-icon="i-lucide-chart-scatter">
    <template #actions>
      <UButton v-if="can('ai.history')" :label="t('nav.aiHistory')" icon="i-lucide-history" color="neutral" variant="outline" :to="{ path: '/ai/history', query: { kind: 'analysis' } }" />
    </template>

    <AiOff v-if="!ai.enabled.value" />
    <AiNotAllowed v-else-if="ai.blocked('forms', 'responses')" :source="ai.blocked('forms', 'responses')!" />
    <template v-else>
      <div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <AiFormPicker v-model="formId" />
        <DataDateRangePicker :from="from" :to="to" @change="setPeriod" />
        <UButton :label="t('ai.analysis.run')" icon="i-lucide-sparkles" color="neutral" :loading="busy" :disabled="!formId" class="sm:ms-auto" @click="run" />
      </div>
      <p class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-coins" class="size-3.5" />{{ t('ai.create.cost', { n: AI_KIND_META.analysis.credits }, AI_KIND_META.analysis.credits) }} · {{ t('ai.analysis.private') }}</p>

      <AiThinking v-if="busy && !analysis" :steps="steps" />
      <AppEmpty v-else-if="failed && !analysis" variant="outline" icon="i-lucide-cloud-alert" :title="t('ai.create.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: run }]" />
      <div v-else-if="analysis" class="flex flex-col gap-4 transition-opacity" :class="busy || stale ? 'opacity-60' : ''" :aria-busy="busy || undefined">
        <UAlert v-if="stale && !busy" color="neutral" variant="subtle" icon="i-lucide-refresh-cw" :title="t('ai.analysis.stale')" :actions="[{ label: t('ai.analysis.run'), color: 'neutral', onClick: run }]" />
        <AiAnalysisView :analysis="analysis" />
      </div>
      <UCard v-else variant="outline" class="shrink-0" :ui="{ body: 'p-6 sm:p-8' }">
        <AppEmpty icon="i-lucide-chart-scatter" :title="t('ai.analysis.emptyTitle')" :description="t('ai.analysis.emptyDesc')" />
      </UCard>

      <AiAskBox v-if="formId" :form-id="formId" class="shrink-0" />
    </template>
  </AppPanel>
</template>
