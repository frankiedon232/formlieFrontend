<!--
  A response in a few lines (F19 M4), in the response panel: "Summarise" asks the assistant (only for people
  who may analyse with it, when it is on and may read responses); the key answers, the tone and what the
  written answers are about. A new response clears it.
-->
<script setup lang="ts">
import type { AiResponseSummary } from '#shared/types/ai'

const props = defineProps<{ responseId: string }>()
const { t, d } = useI18n()
/** Dates in the reader's format; everything else as it was answered. */
const valueOf = (value: string) => (/^\d{4}-\d{2}-\d{2}$/.test(value) ? d(new Date(`${value}T12:00:00`), { day: 'numeric', month: 'long', year: 'numeric' }) : value)
const api = useApi()
const { handle } = useErrorHandler()
const { can } = useCan()
const ai = useAi()
onMounted(() => void ai.load())
const shown = computed(() => can('ai.analyse') && ai.enabled.value && ai.settings.value?.sources.responses !== false)

const summary = ref<AiResponseSummary | null>(null)
const busy = ref(false)
watch(
  () => props.responseId,
  () => (summary.value = null),
)
async function run() {
  if (busy.value) return
  busy.value = true
  try {
    summary.value = (await api.post<AiResponseSummary>(`/ai/responses/${props.responseId}/summary`)).data
  } catch (error) {
    handle(error)
  } finally {
    busy.value = false
  }
}
const TONE = { positive: 'success', neutral: 'neutral', negative: 'error' } as const
</script>

<template>
  <div v-if="shown" class="flex flex-col gap-3 rounded-lg border border-default p-3">
    <div class="flex items-center justify-between gap-2">
      <span class="flex items-center gap-1.5 text-sm font-medium text-highlighted"><UIcon name="i-lucide-sparkles" class="size-4" />{{ t('ai.summary.title') }}</span>
      <UButton v-if="!summary" :label="t('ai.summary.run')" color="neutral" variant="outline" size="xs" :loading="busy" @click="run" />
      <UBadge v-else :label="t('ai.label.made')" color="neutral" variant="soft" size="sm" class="rounded-md" />
    </div>
    <div v-if="busy" class="flex flex-col gap-1.5"><USkeleton v-for="n in 3" :key="n" class="h-4 w-full" /></div>
    <template v-else-if="summary">
      <ul class="flex flex-col gap-1">
        <li v-for="point in summary.points" :key="point.label" class="text-sm"><span class="text-muted">{{ point.label }}:</span> <span class="text-default">{{ valueOf(point.value) }}</span></li>
      </ul>
      <div v-if="summary.sentiment || summary.themes.length" class="flex flex-wrap items-center gap-1.5">
        <UBadge v-if="summary.sentiment" :label="t(`ai.tone.${summary.sentiment}`)" :color="TONE[summary.sentiment]" variant="subtle" size="sm" class="rounded-md" />
        <UBadge v-for="theme in summary.themes" :key="theme" :label="t(`ai.theme.${theme}`)" color="neutral" variant="outline" size="sm" class="rounded-md" />
      </div>
    </template>
    <p v-else class="text-xs text-muted">{{ t('ai.summary.desc') }}</p>
  </div>
</template>
