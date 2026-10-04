<!--
  Edit one submitted answer (F11 M2; people with "Can edit" only). The question appears exactly as
  the respondent filled it in (the renderer's own control) and is checked by the same rules as a
  submission, here and again on the server. Saving records who changed what, before and after, in
  the response's history and the audit trail. A draggable dialog over the response panel.
-->
<script setup lang="ts">
import type { ResponseDetail } from '#shared/types/responses'
import type { FormField } from '#shared/utils/forms/build'
import { validateAnswer } from '#shared/utils/forms/validate'

const props = defineProps<{ response: ResponseDetail; field: FormField | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [response: ResponseDetail] }>()
const { t } = useI18n()
const api = useApi()
const message = useAnswerMessages()
const { busy, run } = useBusy()

const value = ref<unknown>(null)
const error = ref<string>()
const errorParts = ref<string[]>()
const copy = (input: unknown) => (input == null ? null : JSON.parse(JSON.stringify(input)))
const original = computed(() => (props.field ? (props.response.data[props.field.key] ?? null) : null))
watch(
  () => [open.value, props.field?.key] as const,
  ([isOpen]) => {
    if (!isOpen || !props.field) return
    value.value = copy(original.value)
    error.value = undefined
    errorParts.value = undefined
  },
  { immediate: true },
)
watch(value, () => ((error.value = undefined), (errorParts.value = undefined)), { deep: true })
const changed = computed(() => JSON.stringify(value.value ?? null) !== JSON.stringify(original.value))

async function save() {
  const field = props.field
  if (!field || !changed.value) return
  const issue = validateAnswer(field, value.value, !!field.required)
  if (issue) {
    error.value = message(field, issue)
    errorParts.value = issue.parts
    return
  }
  const id = props.response.id
  const result = await run(() => api.patch<ResponseDetail>(`/responses/${id}`, { data: { [field.key]: value.value ?? null } }), {
    success: t('responses.edit.saved'),
  })
  if (!result) return
  emit('saved', result.data)
  open.value = false
}
</script>

<template>
  <AppModal
    v-model:open="open"
    :title="t('responses.edit.title')"
    :description="t('responses.edit.desc', { n: response.number })"
    :dismissible="!busy"
    :ui="{ content: 'sm:max-w-lg' }"
  >
    <template #body>
      <form class="flex flex-col gap-4" @submit.prevent="save">
        <FormsRendererField v-if="field" v-model="value" :field="field" :error="error" :error-parts="errorParts" />
        <p class="flex items-start gap-1.5 text-xs text-muted">
          <UIcon name="i-lucide-history" class="mt-px size-3.5 shrink-0" />
          {{ t('responses.edit.recorded') }}
        </p>
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" :disabled="busy" @click="open = false" />
        <UButton :label="t('responses.edit.save')" icon="i-lucide-check" color="neutral" :loading="busy" :disabled="!changed" @click="save" />
      </div>
    </template>
  </AppModal>
</template>
