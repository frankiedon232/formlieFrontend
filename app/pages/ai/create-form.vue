<!--
  AI assistant → Create a form (F19 M2): describe the form in plain words (or paste a document), get a
  draft with pages, questions, follow-ups and totals, see it as respondents will, then create it and
  open the builder, try again, or put it aside. Nothing is created until the person says so.
-->
<script setup lang="ts">
import type { AiApplyResult, AiFormDraft, AiUsage } from '#shared/types/ai'
import type { FormFolder } from '#shared/types/forms'
import { AI_KIND_META } from '#shared/utils/ai/kinds'

definePageMeta({ breadcrumb: 'nav.aiCreateForm' })
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { can } = useCan()
const ai = useAi()
useHead({ title: () => t('nav.aiCreateForm') })

const prompt = ref('')
const documentText = ref('')
const pages = ref<'auto' | 'one' | 'several'>('auto')
const draft = ref<AiFormDraft | null>(null)
const variant = ref(0)
const asking = ref(false)
const failed = ref(false)
const usage = ref<AiUsage | null>(null)
const left = computed(() => (usage.value ? Math.max(0, usage.value.limit - usage.value.used) : null))
const loadUsage = async () => {
  try {
    usage.value = (await api.get<AiUsage>('/ai/usage', undefined, { background: true })).data
  } catch {
    usage.value = null
  }
}
const folders = ref<{ value: string; label: string }[]>([])
onMounted(async () => {
  void ai.load()
  void loadUsage()
  try {
    folders.value = (await api.get<FormFolder[]>('/folders', undefined, { background: true })).data.map(folder => ({ value: folder.id, label: folder.name }))
  } catch {
    folders.value = []
  }
})

const examples = computed(() => [t('ai.create.example.visitor'), t('ai.create.example.order'), t('ai.create.example.feedback'), t('ai.create.example.leave')])
const steps = computed(() => [t('ai.create.step.read'), t('ai.create.step.questions'), t('ai.create.step.logic'), t('ai.create.step.layout')])

const name = ref('')
const folderId = ref<string | undefined>(undefined)
async function generate(again = false) {
  if (asking.value) return
  asking.value = true
  failed.value = false
  variant.value = again ? variant.value + 1 : 0
  try {
    const previous = again ? draft.value?.request_id : null
    draft.value = null
    draft.value = (await api.post<AiFormDraft>('/ai/forms/draft', { prompt: prompt.value, document: documentText.value || null, pages: pages.value, variant: variant.value, replaces: previous })).data
    name.value = draft.value.name
    void loadUsage()
  } catch (error) {
    failed.value = true
    handle(error)
  } finally {
    asking.value = false
  }
}

const creating = ref(false)
async function create() {
  if (!draft.value || creating.value || !name.value.trim()) return
  creating.value = true
  try {
    const { target } = (await api.post<AiApplyResult>(`/ai/requests/${draft.value.request_id}/apply`, { name: name.value.trim(), folder_id: folderId.value ?? null })).data
    toast.add({ title: t('ai.create.created', { name: target.name }), color: 'success', icon: 'i-lucide-circle-check' })
    await navigateTo(`/forms/${target.id}/build`)
  } catch (error) {
    handle(error)
  } finally {
    creating.value = false
  }
}
const discarding = ref(false)
async function discard() {
  if (!draft.value) return
  discarding.value = true
  try {
    await api.post(`/ai/requests/${draft.value.request_id}/discard`)
    draft.value = null
    toast.add({ title: t('ai.create.discarded'), color: 'neutral', icon: 'i-lucide-archive' })
  } catch (error) {
    handle(error)
  } finally {
    discarding.value = false
  }
}
</script>

<template>
  <AppPanel id="ai-create-form" :title="t('nav.aiCreateForm')" :subtitle="t('ai.section.createForm')" subtitle-icon="i-lucide-file-plus-2">
    <template #actions>
      <UButton v-if="can('ai.history')" :label="t('nav.aiHistory')" icon="i-lucide-history" color="neutral" variant="outline" :to="{ path: '/ai/history', query: { kind: 'form' } }" />
    </template>

    <AiOff v-if="!ai.enabled.value" />
    <div v-else class="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)] xl:gap-6">
      <div class="flex min-w-0 flex-col gap-4 lg:sticky lg:top-0">
        <AiPromptBox
          v-model="prompt"
          v-model:document="documentText"
          v-model:pages="pages"
          :label="t('ai.create.describe')"
          :placeholder="t('ai.create.placeholder')"
          :examples="examples"
          :busy="asking"
          :cost="AI_KIND_META.form.credits"
          :left="left"
          with-document
          with-pages
          @generate="generate()"
        />
        <p class="flex items-start gap-2 px-1 text-xs text-muted"><UIcon name="i-lucide-shield-check" class="mt-0.5 size-3.5 shrink-0" />{{ t('ai.create.private') }}</p>
      </div>

      <div class="flex min-w-0 flex-col gap-4">
        <AiThinking v-if="asking" :steps="steps" />
        <AppEmpty v-else-if="failed && !draft" icon="i-lucide-cloud-alert" :title="t('ai.create.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => generate() }]" variant="outline" />
        <template v-else-if="draft">
          <UCard variant="outline" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-5' }">
            <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
              <UFormField :label="t('ai.create.name')" class="min-w-0 flex-1">
                <UInput v-model="name" :maxlength="120" class="w-full" />
              </UFormField>
              <UFormField v-if="folders.length" :label="t('ai.create.folder')" class="sm:w-52">
                <USelectMenu v-model="folderId" :items="folders" value-key="value" :placeholder="t('ai.create.noFolder')" :search-input="{ placeholder: t('common.search') }" class="w-full" />
              </UFormField>
            </div>
            <AiNotes :notes="draft.notes" :stats="draft.stats" />
            <div class="flex flex-wrap items-center justify-end gap-2 border-t border-default pt-4">
              <UButton :label="t('ai.create.discard')" icon="i-lucide-x" color="neutral" variant="ghost" :loading="discarding" :disabled="creating" @click="discard" />
              <UButton :label="t('ai.create.again')" icon="i-lucide-refresh-cw" color="neutral" variant="outline" :disabled="creating || discarding" @click="generate(true)" />
              <UButton v-if="can('forms.create')" :label="t('ai.create.create')" icon="i-lucide-arrow-right" trailing color="neutral" :loading="creating" :disabled="!name.trim() || discarding" @click="create" />
            </div>
            <UAlert v-if="!can('forms.create')" color="neutral" variant="subtle" icon="i-lucide-lock" :title="t('ai.create.noCreate')" />
          </UCard>
          <TemplatesPreview :schema="draft.schema" :title="name || draft.name" />
        </template>
        <UCard v-else variant="outline" :ui="{ body: 'flex flex-col gap-4 p-6 sm:p-8' }">
          <AppEmpty icon="i-lucide-sparkles" :title="t('ai.create.emptyTitle')" :description="t('ai.create.emptyDesc')" />
          <ul class="mx-auto grid max-w-xl gap-2 text-sm text-muted sm:grid-cols-2">
            <li v-for="tip in ['list', 'document', 'people', 'logic']" :key="tip" class="flex items-start gap-2">
              <UIcon name="i-lucide-lightbulb" class="mt-0.5 size-4 shrink-0 text-default" />{{ t(`ai.create.tip.${tip}`) }}
            </li>
          </ul>
        </UCard>
      </div>
    </div>
  </AppPanel>
</template>
