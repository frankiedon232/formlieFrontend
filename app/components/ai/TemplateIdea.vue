<!--
  Template ideas → Template (F19 M2): describe a use case, get a template with the design that suits
  its kind (the gallery category's look), preview it, then save it to the workspace's templates with a
  name, description and category; try again or put it aside.
-->
<script setup lang="ts">
import type { AiApplyResult, AiTemplateDraft } from '#shared/types/ai'
import { TEMPLATE_CATEGORIES, type TemplateCategoryKey } from '#shared/templates'
import { AI_KIND_META } from '#shared/utils/ai/kinds'

const props = defineProps<{ left: number | null }>()
const emit = defineEmits<{ used: [] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { can } = useCan()

const prompt = ref('')
const draft = ref<AiTemplateDraft | null>(null)
const variant = ref(0)
const asking = ref(false)
const failed = ref(false)
const name = ref('')
const description = ref('')
const category = ref<TemplateCategoryKey>('business')
const categories = computed(() => TEMPLATE_CATEGORIES.map(item => ({ value: item.key, label: t(`templates.categories.${item.key}`), icon: item.icon })))
const examples = computed(() => [t('ai.templates.example.loan'), t('ai.templates.example.inspection'), t('ai.templates.example.volunteer'), t('ai.templates.example.course')])
const steps = computed(() => [t('ai.create.step.read'), t('ai.templates.step.kind'), t('ai.create.step.questions'), t('ai.templates.step.design')])

async function generate(again = false) {
  if (asking.value) return
  asking.value = true
  failed.value = false
  variant.value = again ? variant.value + 1 : 0
  try {
    const previous = again ? draft.value?.request_id : null
    draft.value = null
    draft.value = (await api.post<AiTemplateDraft>('/ai/templates/draft', { prompt: prompt.value, variant: variant.value, replaces: previous })).data
    name.value = draft.value.name
    description.value = prompt.value.trim().slice(0, 300)
    category.value = draft.value.category as TemplateCategoryKey
    emit('used')
  } catch (error) {
    failed.value = true
    handle(error)
  } finally {
    asking.value = false
  }
}

const saving = ref(false)
async function save() {
  if (!draft.value || saving.value || !name.value.trim()) return
  saving.value = true
  try {
    const { target } = (await api.post<AiApplyResult>(`/ai/requests/${draft.value.request_id}/apply`, { name: name.value.trim(), description: description.value.trim(), category: category.value })).data
    toast.add({ title: t('ai.templates.saved', { name: target.name }), color: 'success', icon: 'i-lucide-circle-check' })
    await navigateTo(`/templates/${target.id}`)
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
async function discard() {
  if (!draft.value) return
  try {
    await api.post(`/ai/requests/${draft.value.request_id}/discard`)
    draft.value = null
  } catch (error) {
    handle(error)
  }
}
</script>

<template>
  <div class="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)] xl:gap-6">
    <AiPromptBox v-model="prompt" class="lg:sticky lg:top-0" :label="t('ai.templates.describe')" :placeholder="t('ai.templates.placeholder')" :examples="examples" :busy="asking" :cost="AI_KIND_META.template.credits" :left="props.left" @generate="generate()" />

    <div class="flex min-w-0 flex-col gap-4">
      <AiThinking v-if="asking" :steps="steps" />
      <AppEmpty v-else-if="failed && !draft" variant="outline" icon="i-lucide-cloud-alert" :title="t('ai.create.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => generate() }]" />
      <template v-else-if="draft">
        <UCard variant="outline" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-5' }">
          <div class="grid gap-3 sm:grid-cols-[minmax(0,1fr)_14rem]">
            <UFormField :label="t('ai.templates.name')"><UInput v-model="name" :maxlength="80" class="w-full" /></UFormField>
            <UFormField :label="t('ai.templates.category')">
              <USelectMenu v-model="category" :items="categories" value-key="value" class="w-full" />
            </UFormField>
          </div>
          <UFormField :label="t('ai.templates.description')"><UTextarea v-model="description" :rows="2" autoresize :maxlength="300" class="w-full" /></UFormField>
          <AiNotes :notes="draft.notes" :stats="draft.stats" />
          <div class="flex flex-wrap items-center justify-end gap-2 border-t border-default pt-4">
            <UButton :label="t('ai.create.discard')" icon="i-lucide-x" color="neutral" variant="ghost" :disabled="saving" @click="discard" />
            <UButton :label="t('ai.create.again')" icon="i-lucide-refresh-cw" color="neutral" variant="outline" :disabled="saving" @click="generate(true)" />
            <UButton v-if="can('forms.save_template')" :label="t('ai.templates.save')" icon="i-lucide-layout-template" color="neutral" :loading="saving" :disabled="!name.trim()" @click="save" />
          </div>
          <UAlert v-if="!can('forms.save_template')" color="neutral" variant="subtle" icon="i-lucide-lock" :title="t('ai.templates.noSave')" />
        </UCard>
        <TemplatesPreview :schema="draft.schema" :title="name || draft.name" />
      </template>
      <UCard v-else variant="outline" :ui="{ body: 'p-6 sm:p-8' }">
        <AppEmpty icon="i-lucide-layout-template" :title="t('ai.templates.emptyTitle')" :description="t('ai.templates.emptyDesc')" />
      </UCard>
    </div>
  </div>
</template>
