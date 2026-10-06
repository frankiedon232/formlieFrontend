<!--
  Endpoint wizard, step 1 (F13 M1): which form. Only published forms can be endpoints (what callers
  send must pass the same checks as the form page). Searchable list of the workspace's published
  forms; a draft form says to publish it first.
-->
<script setup lang="ts">
import type { FormSummary } from '#shared/types/forms'

const formId = defineModel<string | null>('formId', { required: true })
const emit = defineEmits<{ picked: [form: { id: string; name: string }] }>()
const { t } = useI18n()
const api = useApi()
const { relative, number } = useFormat()

const forms = ref<FormSummary[] | null>(null)
const q = ref('')
onMounted(async () => {
  try {
    forms.value = (await api.list<FormSummary>('/forms', { 'filter[status]': 'published', page_size: 100, sort: 'name' })).data
  } catch {
    forms.value = []
  }
})
const shown = computed(() => (forms.value ?? []).filter(form => !q.value.trim() || form.name.toLowerCase().includes(q.value.trim().toLowerCase())))
function pick(form: FormSummary) {
  formId.value = form.id
  emit('picked', { id: form.id, name: form.name })
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <UInput v-model="q" icon="i-lucide-search" :placeholder="t('apiService.wizard.searchForms')" class="w-full" :aria-label="t('apiService.wizard.searchForms')" />
    <div v-if="!forms" class="grid gap-2 sm:grid-cols-2"><USkeleton v-for="n in 6" :key="n" class="h-16 rounded-lg" /></div>
    <AppEmpty v-else-if="!forms.length" size="sm" icon="i-lucide-file-x-2" :title="t('apiService.wizard.noForms')" :description="t('apiService.wizard.noFormsDesc')" :actions="[{ label: t('apiService.wizard.toForms'), icon: 'i-lucide-file-text', color: 'neutral', variant: 'outline', to: '/forms' }]" />
    <AppEmpty v-else-if="!shown.length" size="xs" icon="i-lucide-search-x" :title="t('explorer.noMatch')" />
    <div v-else role="radiogroup" :aria-label="t('apiService.wizard.step.form')" class="grid max-h-[26rem] gap-2 overflow-y-auto p-0.5 sm:grid-cols-2">
      <button
        v-for="form in shown"
        :key="form.id"
        type="button"
        role="radio"
        :aria-checked="formId === form.id"
        class="flex min-w-0 items-center gap-3 rounded-lg border p-3 text-start transition-colors focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
        :class="formId === form.id ? 'border-(--ui-border-inverted) bg-elevated/60 ring-1 ring-(--ui-border-inverted)' : 'border-default hover:border-accented hover:bg-elevated/40'"
        @click="pick(form)"
      >
        <span class="flex size-9 shrink-0 items-center justify-center rounded-md border border-default bg-default"><UIcon name="i-lucide-file-text" class="size-4 text-highlighted" /></span>
        <span class="flex min-w-0 flex-1 flex-col">
          <span class="truncate text-sm font-medium text-highlighted">{{ form.name }}</span>
          <span class="truncate text-xs text-muted">{{ t('responses.count', { n: number(form.responses_count) }, form.responses_count) }} · {{ relative(form.updated_at) }}</span>
        </span>
        <UIcon v-if="formId === form.id" name="i-lucide-circle-check" class="size-5 shrink-0 text-highlighted" />
      </button>
    </div>
  </div>
</template>
