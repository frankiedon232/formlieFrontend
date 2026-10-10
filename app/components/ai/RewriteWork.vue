<!--
  Translations → Rewrite (F19 M5): a plain-language check of a form in the tone wanted (plain, friendly,
  formal): only the texts that could be clearer, original and suggestion side by side with why, each one
  kept or not (and editable), the reading age before and after; save the chosen ones into the draft.
-->
<script setup lang="ts">
import { AI_TONES, type AiRewrite, type AiTone } from '#shared/types/ai'
import { AI_KIND_META } from '#shared/utils/ai/kinds'

const emit = defineEmits<{ used: [] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()

const formId = ref<string | undefined>(undefined)
const tone = ref<AiTone>('plain')
const tones = computed(() => AI_TONES.map(value => ({ value, label: t(`ai.rewrite.tone.${value}`) })))
const result = ref<AiRewrite | null>(null)
const texts = ref<Record<string, string>>({})
const keep = ref<Record<string, boolean>>({})
const busy = ref(false)
const failed = ref(false)

async function run() {
  if (!formId.value || busy.value) return
  busy.value = true
  failed.value = false
  try {
    const { data } = await api.post<AiRewrite>(`/ai/forms/${formId.value}/rewrite`, { tone: tone.value })
    result.value = data
    texts.value = Object.fromEntries(data.items.map(item => [item.key, item.rewrite]))
    keep.value = Object.fromEntries(data.items.map(item => [item.key, true]))
    emit('used')
  } catch (error) {
    failed.value = true
    handle(error)
  } finally {
    busy.value = false
  }
}
const chosen = computed(() => Object.fromEntries((result.value?.items ?? []).filter(item => keep.value[item.key] && texts.value[item.key]?.trim()).map(item => [item.key, texts.value[item.key]!.trim()])))
const chosenCount = computed(() => Object.keys(chosen.value).length)
const saving = ref(false)
async function save() {
  if (!result.value || !chosenCount.value || saving.value) return
  saving.value = true
  try {
    await api.post(`/ai/requests/${result.value.request_id}/apply`, { texts: chosen.value })
    toast.add({ title: t('ai.rewrite.saved', { n: chosenCount.value }, chosenCount.value), description: t('ai.translate.savedHint'), color: 'success', icon: 'i-lucide-circle-check', actions: [{ label: t('ai.translate.openBuilder'), color: 'neutral', variant: 'outline', to: `/forms/${result.value.form.id}/build` }] })
    result.value = null
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
      <AiFormPicker v-model="formId" need="edit" />
      <UTabs v-model="tone" :items="tones" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="self-start" />
      <UButton :label="t('ai.rewrite.run')" icon="i-lucide-sparkles" color="neutral" :loading="busy" :disabled="!formId" class="sm:ms-auto" @click="run" />
    </div>
    <p class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-coins" class="size-3.5" />{{ t('ai.create.cost', { n: AI_KIND_META.rewrite.credits }, AI_KIND_META.rewrite.credits) }} · {{ t('ai.rewrite.englishNote') }}</p>

    <AiThinking v-if="busy" :steps="[t('ai.translate.step.read'), t('ai.rewrite.step.check'), t('ai.rewrite.step.write')]" />
    <AppEmpty v-else-if="failed && !result" variant="outline" icon="i-lucide-cloud-alert" :title="t('ai.create.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: run }]" />
    <template v-else-if="result">
      <div class="grid gap-3 sm:grid-cols-3">
        <div class="flex flex-col gap-0.5 rounded-lg border border-default px-4 py-3">
          <span class="text-[11px] text-muted">{{ t('ai.rewrite.readingAge') }}</span>
          <span class="text-xl font-semibold text-highlighted tabular-nums">{{ t('ai.rewrite.years', { before: result.reading.before, after: result.reading.after }) }}</span>
        </div>
        <div class="flex flex-col gap-0.5 rounded-lg border border-default px-4 py-3">
          <span class="text-[11px] text-muted">{{ t('ai.rewrite.clearer') }}</span>
          <span class="text-xl font-semibold text-highlighted tabular-nums">{{ t('ai.rewrite.ofTexts', { n: result.items.length, total: result.total }) }}</span>
        </div>
        <div class="flex flex-col gap-0.5 rounded-lg border border-default px-4 py-3">
          <span class="text-[11px] text-muted">{{ t('ai.rewrite.toneLabel') }}</span>
          <span class="text-xl font-semibold text-highlighted">{{ t(`ai.rewrite.tone.${result.tone}`) }}</span>
        </div>
      </div>
      <UCard variant="outline" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
        <AppEmpty v-if="!result.items.length" size="sm" icon="i-lucide-check-check" :title="t('ai.rewrite.allClear')" />
        <ul v-else class="flex flex-col divide-y divide-default">
          <li v-for="item in result.items" :key="item.key" class="flex flex-col gap-2 py-3">
            <div class="flex items-start gap-3">
              <UCheckbox v-model="keep[item.key]" class="mt-0.5" :aria-label="t('ai.rewrite.keep')" />
              <div class="grid min-w-0 flex-1 gap-2 sm:grid-cols-2 sm:gap-4">
                <p class="text-sm text-muted line-through decoration-(--ui-border-accented)">{{ item.text }}</p>
                <UTextarea v-model="texts[item.key]" :rows="1" autoresize :disabled="!keep[item.key]" class="w-full" :aria-label="t('ai.rewrite.suggestion')" />
              </div>
            </div>
            <div class="flex flex-wrap gap-1.5 ps-8">
              <UBadge v-for="reason in item.reasons" :key="reason" :label="t(`ai.rewrite.reason.${reason}`)" color="neutral" variant="outline" size="sm" class="rounded-md" />
            </div>
          </li>
        </ul>
        <div v-if="result.items.length" class="flex flex-wrap items-center justify-end gap-2 border-t border-default pt-4">
          <span class="me-auto text-xs text-muted">{{ t('ai.rewrite.chosen', { n: chosenCount }, chosenCount) }}</span>
          <UButton :label="t('ai.create.discard')" icon="i-lucide-x" color="neutral" variant="ghost" :disabled="saving" @click="result = null" />
          <UButton :label="t('ai.rewrite.save')" icon="i-lucide-check" color="neutral" :loading="saving" :disabled="!chosenCount" @click="save" />
        </div>
      </UCard>
    </template>
    <UCard v-else variant="outline" :ui="{ body: 'p-6 sm:p-8' }">
      <AppEmpty icon="i-lucide-pen-line" :title="t('ai.rewrite.emptyTitle')" :description="t('ai.rewrite.emptyDesc')" />
    </UCard>
  </div>
</template>
