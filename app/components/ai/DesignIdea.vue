<!--
  Template ideas → Design (F19 M2): a brand colour (the workspace's by default) and, optionally, the
  feel wanted ("calm", "bold", "formal") → three designs that keep the colour readable, previewed on a
  sample form; pick one and save it to Themes.
-->
<script setup lang="ts">
import type { AiApplyResult, AiThemeDraft } from '#shared/types/ai'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { AI_KIND_META } from '#shared/utils/ai/kinds'

const props = defineProps<{ left: number | null; brand: string | null }>()
const emit = defineEmits<{ used: [] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { can } = useCan()
const { number } = useFormat()

const colour = ref(props.brand && /^#[0-9a-f]{6}$/i.test(props.brand) ? props.brand.toLowerCase() : '#0f766e')
watch(
  () => props.brand,
  value => value && /^#[0-9a-f]{6}$/i.test(value) && !draft.value && (colour.value = value.toLowerCase()),
)
const mood = ref('')
const draft = ref<AiThemeDraft | null>(null)
const picked = ref<string | null>(null)
const asking = ref(false)
const failed = ref(false)
const name = ref('')
const steps = computed(() => [t('ai.design.step.colour'), t('ai.design.step.contrast'), t('ai.design.step.styles')])
const ready = computed(() => /^#[0-9a-f]{6}$/i.test(colour.value) && !asking.value && (props.left === null || props.left >= AI_KIND_META.theme.credits))

async function generate() {
  if (!ready.value) return
  asking.value = true
  failed.value = false
  try {
    const previous = draft.value?.request_id ?? null
    draft.value = null
    draft.value = (await api.post<AiThemeDraft>('/ai/themes/draft', { colour: colour.value, mood: mood.value, replaces: previous })).data
    picked.value = draft.value.suggestions[0]?.key ?? null
    name.value = t('ai.design.defaultName', { colour: colour.value.toUpperCase() })
    emit('used')
  } catch (error) {
    failed.value = true
    handle(error)
  } finally {
    asking.value = false
  }
}
const chosen = computed(() => draft.value?.suggestions.find(item => item.key === picked.value) ?? null)
const preview = computed<FormSchemaV1 | null>(() => (draft.value && chosen.value ? { ...draft.value.sample, theme: chosen.value.tokens } : null))
const swatches = (tokens: Record<string, unknown>) => {
  const colors = tokens.colors as Record<string, string>
  const page = tokens.page as Record<string, string>
  return [colors.primary, page.bg, colors.input_border, colors.text]
}

const saving = ref(false)
async function save() {
  if (!draft.value || !chosen.value || saving.value || !name.value.trim()) return
  saving.value = true
  try {
    const { target } = (await api.post<AiApplyResult>(`/ai/requests/${draft.value.request_id}/apply`, { name: name.value.trim(), key: chosen.value.key })).data
    toast.add({ title: t('ai.design.saved', { name: target.name }), color: 'success', icon: 'i-lucide-circle-check' })
    await navigateTo('/settings/themes')
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
defineShortcuts({ meta_enter: { usingInput: true, handler: () => void generate() } })
</script>

<template>
  <div class="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)] xl:gap-6">
    <UCard variant="outline" class="lg:sticky lg:top-0" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-5' }">
      <FormsDesignerColorField v-model="colour" :label="t('ai.design.colour')" />
      <p v-if="brand" class="-mt-2 text-xs text-muted">{{ t('ai.design.brandHint') }}</p>
      <UFormField :label="t('ai.design.mood')" :hint="t('ai.design.optional')">
        <UInput v-model="mood" :placeholder="t('ai.design.moodPlaceholder')" :maxlength="200" class="w-full" />
      </UFormField>
      <div class="flex flex-wrap items-center justify-between gap-3 border-t border-default pt-4">
        <span class="flex items-center gap-1.5 text-xs text-muted">
          <UIcon name="i-lucide-coins" class="size-3.5" />
          {{ left === null ? t('ai.create.cost', { n: AI_KIND_META.theme.credits }, AI_KIND_META.theme.credits) : t('ai.create.costLeft', { n: AI_KIND_META.theme.credits, left: number(left) }, AI_KIND_META.theme.credits) }}
        </span>
        <UButton :label="t('ai.design.generate')" icon="i-lucide-palette" color="neutral" :loading="asking" :disabled="!ready" @click="generate">
          <template #trailing><UKbd value="meta" size="sm" class="hidden sm:inline-flex" /><UKbd value="enter" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
      </div>
    </UCard>

    <div class="flex min-w-0 flex-col gap-4">
      <AiThinking v-if="asking" :steps="steps" />
      <AppEmpty v-else-if="failed && !draft" variant="outline" icon="i-lucide-cloud-alert" :title="t('ai.create.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: generate }]" />
      <template v-else-if="draft">
        <div class="grid gap-3 sm:grid-cols-3" role="radiogroup" :aria-label="t('ai.design.choose')">
          <button
            v-for="item in draft.suggestions"
            :key="item.key"
            type="button"
            role="radio"
            :aria-checked="picked === item.key"
            class="flex h-full flex-col gap-2 rounded-lg border p-3 text-start transition-all hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
            :class="picked === item.key ? 'border-inverted ring-1 ring-(--ui-border-inverted)' : 'border-default'"
            @click="picked = item.key"
          >
            <span class="flex items-center justify-between gap-2">
              <span class="text-sm font-semibold text-highlighted">{{ t(`ai.design.style.${item.key}.name`) }}</span>
              <UIcon v-if="picked === item.key" name="i-lucide-circle-check" class="size-4 text-highlighted" />
            </span>
            <span class="flex gap-1">
              <span v-for="(swatch, index) in swatches(item.tokens)" :key="index" class="size-5 rounded-md border border-default" :style="{ background: swatch }" />
            </span>
            <span class="text-xs text-muted">{{ t(`ai.design.style.${item.key}.desc`) }}</span>
          </button>
        </div>
        <UCard variant="outline" :ui="{ body: 'flex flex-col gap-3 p-4 sm:flex-row sm:items-end' }">
          <UFormField :label="t('ai.design.name')" class="min-w-0 flex-1"><UInput v-model="name" :maxlength="60" class="w-full" /></UFormField>
          <div class="flex flex-wrap gap-2">
            <UButton :label="t('ai.create.again')" icon="i-lucide-refresh-cw" color="neutral" variant="outline" :disabled="saving" @click="generate" />
            <UButton v-if="can('themes.create')" :label="t('ai.design.save')" icon="i-lucide-paintbrush" color="neutral" :loading="saving" :disabled="!name.trim() || !chosen" @click="save" />
          </div>
        </UCard>
        <UAlert v-if="!can('themes.create')" color="neutral" variant="subtle" icon="i-lucide-lock" :title="t('ai.design.noSave')" />
        <TemplatesPreview v-if="preview" :schema="preview" :title="t('ai.design.sampleTitle')" />
      </template>
      <UCard v-else variant="outline" :ui="{ body: 'p-6 sm:p-8' }">
        <AppEmpty icon="i-lucide-palette" :title="t('ai.design.emptyTitle')" :description="t('ai.design.emptyDesc')" />
      </UCard>
    </div>
  </div>
</template>
