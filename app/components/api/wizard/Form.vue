<!--
  Endpoint wizard, step 1 (F13 M1; channels since owner 2026-10-06): which form. An endpoint answers
  with a form's published version (callers pass the same checks as the form page), so only published
  forms open to the API service are listed. Nothing here changes a form (owner, 2026-10-06: a
  one-click publish next to the list was too easy to hit by mistake); when none is ready, the empty
  state says what to do in the form and links to Forms.
-->
<script setup lang="ts">
import { channelsOf, type FormSummary } from '#shared/types/forms'

const formId = defineModel<string | null>('formId', { required: true })
const emit = defineEmits<{ picked: [form: { id: string; name: string }] }>()
const { t } = useI18n()
const api = useApi()
const { relative, number } = useFormat()

const forms = ref<FormSummary[] | null>(null)
const q = ref('')
async function load() {
  try {
    forms.value = (await api.list<FormSummary>('/forms', { 'filter[status]': 'published', page_size: 100, sort: 'name' })).data
  } catch {
    forms.value = []
  }
}
onMounted(load)
const match = (form: FormSummary) => !q.value.trim() || form.name.toLowerCase().includes(q.value.trim().toLowerCase())
const open = computed(() => (forms.value ?? []).filter(form => form.status === 'published' && channelsOf(form).includes('api')))
const ready = computed(() => open.value.filter(match))
function pick(form: FormSummary) {
  formId.value = form.id
  emit('picked', { id: form.id, name: form.name })
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <UInput v-model="q" icon="i-lucide-search" :placeholder="t('apiService.wizard.searchForms')" class="w-full" :aria-label="t('apiService.wizard.searchForms')" />
    <div v-if="!forms" class="grid gap-2 sm:grid-cols-2"><USkeleton v-for="n in 6" :key="n" class="h-16 rounded-lg" /></div>
    <AppEmpty v-else-if="!open.length" size="sm" icon="i-lucide-file-x-2" :title="t('apiService.wizard.noForms')" :description="t('apiService.wizard.noFormsDesc')" :actions="[{ label: t('apiService.wizard.toForms'), icon: 'i-lucide-file-text', color: 'neutral', variant: 'outline', to: '/forms' }]" />
    <AppEmpty v-else-if="!ready.length" size="xs" icon="i-lucide-search-x" :title="t('explorer.noMatch')" />
    <template v-else>
      <div role="radiogroup" :aria-label="t('apiService.wizard.step.form')" class="grid max-h-[22rem] gap-2 overflow-y-auto p-0.5 sm:grid-cols-2">
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
    </template>
  </div>
</template>
