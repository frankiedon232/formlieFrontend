<!--
  Endpoint wizard, step 1 (F13 M1; channels since owner 2026-10-06): which form. An endpoint answers
  with a form's published version (callers pass the same checks as the form page), and the form must
  be open to the API service. Ready forms can be picked; below them, drafts with "Publish for the API
  only" (sets the form to API only, then publishes it: it never gets a web address) and published
  forms not open to the API with "Open to the API".
-->
<script setup lang="ts">
import { channelsOf, type FormShareSettings, type FormSummary } from '#shared/types/forms'

const formId = defineModel<string | null>('formId', { required: true })
const emit = defineEmits<{ picked: [form: { id: string; name: string }] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { relative, number } = useFormat()

const forms = ref<FormSummary[] | null>(null)
const q = ref('')
async function load() {
  try {
    forms.value = (await api.list<FormSummary>('/forms', { 'filter[status]': 'published,draft', page_size: 100, sort: 'name' })).data
  } catch {
    forms.value = []
  }
}
onMounted(load)
const match = (form: FormSummary) => !q.value.trim() || form.name.toLowerCase().includes(q.value.trim().toLowerCase())
const ready = computed(() => (forms.value ?? []).filter(form => form.status === 'published' && channelsOf(form).includes('api') && match(form)))
const drafts = computed(() => (forms.value ?? []).filter(form => form.status === 'draft' && match(form)))
const closed = computed(() => (forms.value ?? []).filter(form => form.status === 'published' && !channelsOf(form).includes('api') && match(form)))
function pick(form: FormSummary) {
  formId.value = form.id
  emit('picked', { id: form.id, name: form.name })
}

// One click: the form becomes usable here (and picked)
const busy = ref<string | null>(null)
async function makeReady(form: FormSummary, publish: boolean) {
  if (busy.value) return
  busy.value = form.id
  try {
    const share = (await api.put<FormShareSettings>(`/forms/${form.id}/share`, { row_version: form.row_version, channels: publish ? ['api'] : [...channelsOf(form), 'api'] })).data
    if (publish) await api.post(`/forms/${form.id}/publish`, { row_version: share.row_version, change_summary: null })
    toast.add({ title: publish ? t('apiService.wizard.publishedForApi', { name: form.name }) : t('apiService.wizard.openedToApi', { name: form.name }), color: 'success', icon: 'i-lucide-circle-check' })
    await load()
    const fresh = forms.value?.find(item => item.id === form.id)
    if (fresh) pick(fresh)
  } catch (error) {
    handle(error)
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <UInput v-model="q" icon="i-lucide-search" :placeholder="t('apiService.wizard.searchForms')" class="w-full" :aria-label="t('apiService.wizard.searchForms')" />
    <div v-if="!forms" class="grid gap-2 sm:grid-cols-2"><USkeleton v-for="n in 6" :key="n" class="h-16 rounded-lg" /></div>
    <AppEmpty v-else-if="!forms.length" size="sm" icon="i-lucide-file-x-2" :title="t('apiService.wizard.noForms')" :description="t('apiService.wizard.noFormsDesc')" :actions="[{ label: t('apiService.wizard.toForms'), icon: 'i-lucide-file-text', color: 'neutral', variant: 'outline', to: '/forms' }]" />
    <AppEmpty v-else-if="!ready.length && !drafts.length && !closed.length" size="xs" icon="i-lucide-search-x" :title="t('explorer.noMatch')" />
    <template v-else>
      <div v-if="ready.length" role="radiogroup" :aria-label="t('apiService.wizard.step.form')" class="grid max-h-[22rem] gap-2 overflow-y-auto p-0.5 sm:grid-cols-2">
        <button
          v-for="form in ready"
          :key="form.id"
          type="button"
          role="radio"
          :aria-checked="formId === form.id"
          class="flex min-w-0 items-center gap-3 rounded-lg border p-3 text-start transition-colors focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
          :class="formId === form.id ? 'border-(--ui-border-inverted) bg-elevated/60 ring-1 ring-(--ui-border-inverted)' : 'border-default hover:border-accented hover:bg-elevated/40'"
          @click="pick(form)"
        >
          <span class="flex size-9 shrink-0 items-center justify-center rounded-md border border-default bg-default"><UIcon :name="channelsOf(form).length === 1 ? 'i-lucide-code-xml' : 'i-lucide-file-text'" class="size-4 text-highlighted" /></span>
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="flex min-w-0 items-center gap-1.5">
              <span class="truncate text-sm font-medium text-highlighted">{{ form.name }}</span>
              <UBadge v-if="channelsOf(form).length === 1" :label="t('forms.channels.apiOnly')" color="neutral" variant="soft" size="xs" class="shrink-0 rounded-md" />
            </span>
            <span class="truncate text-xs text-muted">{{ t('responses.count', { n: number(form.responses_count) }, form.responses_count) }} · {{ relative(form.updated_at) }}</span>
          </span>
          <UIcon v-if="formId === form.id" name="i-lucide-circle-check" class="size-5 shrink-0 text-highlighted" />
        </button>
      </div>

      <div v-if="drafts.length || closed.length" class="flex flex-col gap-2">
        <span class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('apiService.wizard.notReady') }}</span>
        <div class="flex max-h-60 flex-col gap-2 overflow-y-auto p-0.5">
          <div v-for="form in [...drafts, ...closed]" :key="form.id" class="flex flex-wrap items-center gap-3 rounded-lg border border-dashed border-default p-3" :class="busy === form.id ? 'opacity-60' : ''">
            <span class="flex size-9 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="form.status === 'draft' ? 'i-lucide-file-pen' : 'i-lucide-globe-lock'" class="size-4 text-muted" /></span>
            <span class="flex min-w-0 flex-1 flex-col">
              <span class="truncate text-sm font-medium text-highlighted">{{ form.name }}</span>
              <span class="text-xs text-muted">{{ form.status === 'draft' ? t('apiService.wizard.draftHint') : t('apiService.wizard.closedHint') }}</span>
            </span>
            <div class="flex shrink-0 gap-2">
              <UButton :label="t('apiService.actions.openForm')" color="neutral" variant="ghost" size="xs" :to="`/forms/${form.id}`" target="_blank" />
              <UButton
                :label="form.status === 'draft' ? t('apiService.wizard.publishForApi') : t('apiService.wizard.openToApi')"
                :icon="form.status === 'draft' ? 'i-lucide-rocket' : 'i-lucide-code-xml'"
                color="neutral"
                size="xs"
                :loading="busy === form.id"
                :disabled="!!busy && busy !== form.id"
                @click="makeReady(form, form.status === 'draft')"
              />
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
