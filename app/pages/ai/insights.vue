<!--
  AI assistant → Insights & summaries (F19 M4): a digest of a form's week, month or quarter (responses and
  the change, tone, themes, ratings, what stands out) with "Copy as text" for an email or a report. Single
  responses are summarised from their panel in Responses.
-->
<script setup lang="ts">
import type { AiAnalysis } from '#shared/types/ai'
import { AI_KIND_META } from '#shared/utils/ai/kinds'

definePageMeta({ breadcrumb: 'nav.aiInsights' })
const { t, d } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const { handle } = useErrorHandler()
const { can } = useCan()
const { copy } = useClipboard({ legacy: true })
const ai = useAi()
useHead({ title: () => t('nav.aiInsights') })
onMounted(() => void ai.load())

const formId = computed({
  get: () => (typeof route.query.form === 'string' ? route.query.form : undefined),
  set: value => void router.replace({ query: { ...route.query, form: value } }),
})
const period = computed({
  get: () => (['month', 'quarter'].includes(String(route.query.period)) ? (route.query.period as 'month' | 'quarter') : 'week'),
  set: value => void router.replace({ query: { ...route.query, period: value === 'week' ? undefined : value } }),
})
const periods = computed(() => (['week', 'month', 'quarter'] as const).map(value => ({ value, label: t(`ai.insights.period.${value}`) })))

const digest = ref<AiAnalysis | null>(null)
const busy = ref(false)
const failed = ref(false)
async function run() {
  if (!formId.value || busy.value) return
  busy.value = true
  failed.value = false
  try {
    digest.value = (await api.post<AiAnalysis>('/ai/digest', { form_id: formId.value, period: period.value })).data
  } catch (error) {
    failed.value = true
    handle(error)
  } finally {
    busy.value = false
  }
}
const steps = computed(() => [t('ai.analysis.step.read'), t('ai.analysis.step.themes'), t('ai.insights.step.write')])

/** The digest as plain text in the reader's language (for an email or a report). */
function copyText() {
  const value = digest.value
  if (!value) return
  const day = (date: string) => d(new Date(`${date}T12:00:00`), { day: 'numeric', month: 'long', year: 'numeric' })
  const lines = [
    `${value.form.name}: ${t('ai.range', { from: day(value.period.from), to: day(value.period.to) })}`,
    t('ai.insights.text.responses', { n: value.totals.responses, before: value.totals.previous }),
    t('ai.insights.text.tone', { positive: value.sentiment.positive, neutral: value.sentiment.neutral, negative: value.sentiment.negative }),
    ...value.themes.filter(theme => theme.key !== 'other').slice(0, 5).map(theme => `• ${t(`ai.theme.${theme.key}`)}: ${theme.share}%`),
    ...value.ratings.map(rating => `• ${rating.label}: ${rating.average} / ${rating.max}`),
    ...value.findings.map(note => `• ${t(`ai.note.${note.code}`, { ...note.params, ...(note.theme ? { theme: t(`ai.theme.${note.theme}`) } : {}), ...(typeof note.params?.day === 'string' ? { day: day(note.params.day) } : {}) }, typeof note.params?.n === 'number' ? note.params.n : 1)}`),
    '',
    t('ai.label.made'),
  ]
  void copy(lines.join('\n'))
  toast.add({ title: t('ai.insights.copied'), color: 'success', icon: 'i-lucide-check' })
}
</script>

<template>
  <AppPanel id="ai-insights" :title="t('nav.aiInsights')" :subtitle="t('ai.section.insights')" subtitle-icon="i-lucide-lightbulb">
    <template #actions>
      <UButton v-if="digest" :label="t('ai.insights.copy')" icon="i-lucide-copy" color="neutral" variant="outline" @click="copyText" />
      <UButton v-if="can('ai.history')" :label="t('nav.aiHistory')" icon="i-lucide-history" color="neutral" variant="outline" class="max-sm:hidden" :to="{ path: '/ai/history', query: { kind: 'summary' } }" />
    </template>

    <AiOff v-if="!ai.enabled.value" />
    <AiNotAllowed v-else-if="ai.blocked('forms', 'responses')" :source="ai.blocked('forms', 'responses')!" />
    <template v-else>
      <div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <AiFormPicker v-model="formId" />
        <UTabs v-model="period" :items="periods" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="self-start" />
        <UButton :label="t('ai.insights.run')" icon="i-lucide-sparkles" color="neutral" :loading="busy" :disabled="!formId" class="sm:ms-auto" @click="run" />
      </div>
      <p class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-coins" class="size-3.5" />{{ t('ai.create.cost', { n: AI_KIND_META.summary.credits }, AI_KIND_META.summary.credits) }} · {{ t('ai.insights.single') }}</p>

      <AiThinking v-if="busy && !digest" :steps="steps" />
      <AppEmpty v-else-if="failed && !digest" variant="outline" icon="i-lucide-cloud-alert" :title="t('ai.create.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: run }]" />
      <div v-else-if="digest" class="transition-opacity" :class="busy ? 'opacity-60' : ''" :aria-busy="busy || undefined">
        <AiAnalysisView :analysis="digest" />
      </div>
      <UCard v-else variant="outline" :ui="{ body: 'p-6 sm:p-8' }">
        <AppEmpty icon="i-lucide-lightbulb" :title="t('ai.insights.emptyTitle')" :description="t('ai.insights.emptyDesc')" />
      </UCard>
    </template>
  </AppPanel>
</template>
