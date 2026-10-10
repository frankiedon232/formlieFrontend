<!-- Pick a form whose responses this person may see (F19 M4), searchable; empty state when there is none. -->
<script setup lang="ts">
import type { FormSummary } from '#shared/types/forms'

const model = defineModel<string | undefined>({ required: true })
/** responses = forms whose responses they may see (analysis); edit = forms they may change (translate, rewrite). */
const props = withDefaults(defineProps<{ need?: 'responses' | 'edit' }>(), { need: 'responses' })
const { t } = useI18n()
const api = useApi()
const forms = ref<{ value: string; label: string; description: string }[] | null>(null)
onMounted(async () => {
  try {
    const { data } = await api.list<FormSummary>('/forms', { page_size: 100, sort: '-responses_count' }, { background: true })
    forms.value = data.filter(form => (props.need === 'edit' ? form.can?.edit !== false : form.responses_can?.view !== false) && form.status !== 'archived').map(form => ({ value: form.id, label: form.name, description: t('ai.analysis.responses', { n: form.responses_count }, form.responses_count) }))
    if (!model.value && forms.value[0]) model.value = forms.value[0].value
  } catch {
    forms.value = []
  }
})
</script>

<template>
  <USkeleton v-if="!forms" class="h-8 w-full sm:w-72" />
  <USelectMenu
    v-else
    v-model="model"
    :items="forms"
    value-key="value"
    :placeholder="t('ai.analysis.pickForm')"
    :search-input="{ placeholder: t('common.search') }"
    icon="i-lucide-file-text"
    class="w-full sm:w-72"
    :aria-label="t('ai.analysis.form')"
  />
</template>
