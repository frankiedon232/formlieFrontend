<!--
  New service / edit service (F13 M1): a name (unique in the organisation), what it is for, and
  whether its endpoints answer. A dialog people type in, so an outside click doesn't close it.
-->
<script setup lang="ts">
import { z } from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'
import type { ApiService, ApiServiceSaveRequest } from '#shared/types/apiService'

const props = defineProps<{ service?: ApiService | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [service: ApiService] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()

const schema = z.object({
  name: z.string().trim().min(1, t('apiService.invalid.required')).max(80),
  description: z.string().trim().max(300),
  active: z.boolean(),
})
const state = reactive({ name: '', description: '', active: true })
watch(open, value => {
  if (!value) return
  state.name = props.service?.name ?? ''
  state.description = props.service?.description ?? ''
  state.active = (props.service?.status ?? 'active') === 'active'
})
const form = useTemplateRef<{ setErrors: (errors: { name: string; message: string }[]) => void }>('form')
const saving = ref(false)
async function submit(event: FormSubmitEvent<z.infer<typeof schema>>) {
  if (saving.value) return
  saving.value = true
  try {
    const body: ApiServiceSaveRequest = { name: event.data.name, description: event.data.description || null, status: event.data.active ? 'active' : 'disabled' }
    const { data } = props.service ? await api.patch<ApiService>(`/api-services/${props.service.id}`, body) : await api.post<ApiService>('/api-services', body)
    emit('saved', data)
    open.value = false
  } catch (error) {
    const normalised = handle(error, { silent: true })
    if (normalised.code === 'FRM-API-1003') form.value?.setErrors([{ name: 'name', message: t('errors.FRM-API-1003') }])
    else handle(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="service ? t('apiService.service.editTitle') : t('apiService.service.newTitle')" :description="t('apiService.service.desc')">
    <template #body>
      <UForm id="api-service-form" ref="form" :schema="schema" :state="state" class="flex flex-col gap-4" @submit="submit">
        <UFormField name="name" :label="t('apiService.service.name')" :hint="`${state.name.length}/80`" required>
          <UInput v-model="state.name" :placeholder="t('apiService.service.namePlaceholder')" class="w-full" autofocus maxlength="80" />
        </UFormField>
        <UFormField name="description" :label="t('apiService.service.description')" :hint="t('apiService.optional')">
          <UTextarea v-model="state.description" :rows="3" autoresize class="w-full" maxlength="300" :placeholder="t('apiService.service.descriptionPlaceholder')" />
        </UFormField>
        <UFormField name="active">
          <USwitch v-model="state.active" :label="t('apiService.service.active')" :description="t('apiService.service.activeHint')" />
        </UFormField>
      </UForm>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
        <UButton type="submit" form="api-service-form" :label="service ? t('common.save') : t('apiService.service.create')" color="neutral" :loading="saving" />
      </div>
    </template>
  </AppModal>
</template>
