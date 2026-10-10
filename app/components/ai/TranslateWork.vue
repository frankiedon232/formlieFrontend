<!--
  Translations → Translate (F19 M5): pick a form you may edit and the languages, the assistant translates its
  texts; review side by side per language (original · translation, editable), then save them into the form's
  draft (respondents see them once it is published). What the assistant couldn't translate stays for a person,
  marked, and can be typed here or later in the builder.
-->
<script setup lang="ts">
import type { AiTranslation } from '#shared/types/ai'
import { AI_KIND_META } from '#shared/utils/ai/kinds'
import { APP_LOCALES } from '#shared/utils/i18n/locales'

const props = defineProps<{ left: number | null }>()
const emit = defineEmits<{ used: [] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { number } = useFormat()

const formId = ref<string | undefined>(undefined)
const languages = ref<string[]>([])
const options = computed(() => APP_LOCALES.map(locale => ({ value: locale.code, label: locale.name, icon: locale.flag })))
const cost = computed(() => AI_KIND_META.translate.credits * Math.max(1, languages.value.length))
const result = ref<AiTranslation | null>(null)
const drafts = ref<Record<string, Record<string, string>>>({})
const tab = ref('')
const busy = ref(false)
const failed = ref(false)

async function run() {
  if (!formId.value || !languages.value.length || busy.value) return
  busy.value = true
  failed.value = false
  try {
    const { data } = await api.post<AiTranslation>(`/ai/forms/${formId.value}/translate`, { languages: languages.value })
    result.value = data
    drafts.value = Object.fromEntries(data.languages.map(language => [language.code, Object.fromEntries(language.items.map(item => [item.key, item.translation ?? item.existing ?? '']))]))
    tab.value = data.languages[0]?.code ?? ''
    emit('used')
  } catch (error) {
    failed.value = true
    handle(error)
  } finally {
    busy.value = false
  }
}
const localeOf = (code: string) => APP_LOCALES.find(locale => locale.code === code)
const current = computed(() => result.value?.languages.find(language => language.code === tab.value) ?? null)
const tabs = computed(() => (result.value?.languages ?? []).map(language => ({ value: language.code, label: localeOf(language.code)?.name ?? language.code, icon: localeOf(language.code)?.flag })))
/** What would be saved: texts with something new in them. */
const changes = computed(() => {
  const out: Record<string, Record<string, string>> = {}
  for (const language of result.value?.languages ?? [])
    for (const item of language.items) {
      const value = drafts.value[language.code]?.[item.key]?.trim()
      if (value && value !== item.existing) (out[language.code] ??= {})[item.key] = value
    }
  return out
})
const changeCount = computed(() => Object.values(changes.value).reduce((sum, texts) => sum + Object.keys(texts).length, 0))
const stateOf = (item: AiTranslation['languages'][number]['items'][number]) => (item.translation ? 'assistant' : item.existing ? 'existing' : 'person')
const STATE_ICON = { assistant: 'i-lucide-sparkles', existing: 'i-lucide-check', person: 'i-lucide-pencil' } as const

const saving = ref(false)
async function save() {
  if (!result.value || !changeCount.value || saving.value) return
  saving.value = true
  try {
    await api.post(`/ai/requests/${result.value.request_id}/apply`, { translations: changes.value })
    toast.add({ title: t('ai.translate.saved', { n: changeCount.value }, changeCount.value), description: t('ai.translate.savedHint'), color: 'success', icon: 'i-lucide-circle-check', actions: [{ label: t('ai.translate.openBuilder'), color: 'neutral', variant: 'outline', to: `/forms/${result.value.form.id}/build` }] })
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
      <USelectMenu v-model="languages" :items="options" value-key="value" multiple :placeholder="t('ai.translate.pickLanguages')" :search-input="{ placeholder: t('common.search') }" icon="i-lucide-languages" class="w-full sm:w-72" :aria-label="t('ai.translate.languages')" />
      <UButton :label="t('ai.translate.run')" icon="i-lucide-sparkles" color="neutral" :loading="busy" :disabled="!formId || !languages.length || (props.left !== null && props.left < cost)" class="sm:ms-auto" @click="run" />
    </div>
    <p class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-coins" class="size-3.5" />{{ t('ai.translate.cost', { n: cost }) }}{{ props.left !== null ? ` · ${t('ai.usage.left', { n: number(props.left) })}` : '' }}</p>

    <AiThinking v-if="busy" :steps="[t('ai.translate.step.read'), t('ai.translate.step.translate'), t('ai.translate.step.check')]" />
    <AppEmpty v-else-if="failed && !result" variant="outline" icon="i-lucide-cloud-alert" :title="t('ai.create.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: run }]" />
    <template v-else-if="result && current">
      <UTabs v-model="tab" :items="tabs" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="self-start" />
      <UCard variant="outline" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
        <div class="flex flex-wrap items-center gap-2">
          <UBadge :label="t('ai.translate.byAssistant', { n: current.translated }, current.translated)" icon="i-lucide-sparkles" color="neutral" variant="soft" size="sm" class="rounded-md" />
          <UBadge v-if="current.missing" :label="t('ai.translate.forPerson', { n: current.missing }, current.missing)" icon="i-lucide-pencil" color="warning" variant="subtle" size="sm" class="rounded-md" />
          <span class="ms-auto text-xs text-muted">{{ t('ai.translate.reviewHint') }}</span>
        </div>
        <ul class="flex flex-col divide-y divide-default">
          <li v-for="item in current.items" :key="item.key" class="grid gap-2 py-3 sm:grid-cols-2 sm:gap-4">
            <div class="flex min-w-0 items-start gap-2">
              <UIcon :name="STATE_ICON[stateOf(item)]" class="mt-0.5 size-3.5 shrink-0" :class="stateOf(item) === 'person' ? 'text-warning' : 'text-muted'" :aria-label="t(`ai.translate.state.${stateOf(item)}`)" />
              <p class="min-w-0 text-sm text-default" :dir="localeOf(result.from)?.dir">{{ item.kind === 'html' ? item.text.replace(/<[^>]*>/g, ' ') : item.text }}</p>
            </div>
            <UTextarea
              v-if="item.kind !== 'text'"
              v-model="drafts[current.code]![item.key]"
              :rows="2"
              autoresize
              :placeholder="item.kind === 'html' ? t('ai.translate.htmlInBuilder') : t('ai.translate.typeHere')"
              :disabled="item.kind === 'html'"
              :dir="localeOf(current.code)?.dir"
              class="w-full"
              :aria-label="t('builder.translate.into', { text: item.text, language: localeOf(current.code)?.name ?? current.code })"
            />
            <UInput v-else v-model="drafts[current.code]![item.key]" :placeholder="t('ai.translate.typeHere')" :dir="localeOf(current.code)?.dir" class="w-full" :color="stateOf(item) === 'person' && !drafts[current.code]![item.key] ? 'warning' : undefined" :highlight="stateOf(item) === 'person' && !drafts[current.code]![item.key]" :aria-label="t('builder.translate.into', { text: item.text, language: localeOf(current.code)?.name ?? current.code })" />
          </li>
        </ul>
        <div class="flex flex-wrap items-center justify-end gap-2 border-t border-default pt-4">
          <span class="me-auto text-xs text-muted">{{ t('ai.translate.toSave', { n: changeCount }, changeCount) }}</span>
          <UButton :label="t('ai.create.discard')" icon="i-lucide-x" color="neutral" variant="ghost" :disabled="saving" @click="result = null" />
          <UButton :label="t('ai.translate.save')" icon="i-lucide-check" color="neutral" :loading="saving" :disabled="!changeCount" @click="save" />
        </div>
      </UCard>
    </template>
    <UCard v-else variant="outline" :ui="{ body: 'p-6 sm:p-8' }">
      <AppEmpty icon="i-lucide-languages" :title="t('ai.translate.emptyTitle')" :description="t('ai.translate.emptyDesc')" />
    </UCard>
  </div>
</template>
