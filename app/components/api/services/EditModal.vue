<!--
  New service / edit service (F13 M1; guided in steps since M7, owner 2026-10-06). Allowed websites for
  browser callers (CORS, leftovers L6). New: 1 What a
  service is (and where it sits in the setup) → 2 Name and description → 3 Created, and what comes
  next (an endpoint, with a button straight to it). Editing goes straight to the details. With
  `:next="false"` (the endpoint wizard's own "create a service first") it closes after saving.
  A dialog people type in, so an outside click doesn't close it.
-->
<script setup lang="ts">
import { z } from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'
import type { ApiService, ApiServiceSaveRequest } from '#shared/types/apiService'
import { MAX_ALLOWED_ORIGINS, normaliseOrigin } from '#shared/utils/apiService/origins'

const props = withDefaults(defineProps<{ service?: ApiService | null; next?: boolean }>(), { service: null, next: true })
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [service: ApiService] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const setup = useApiSetup()
const { can } = useCan()

const schema = z.object({
  name: z.string().trim().min(1, t('apiService.invalid.required')).max(80),
  description: z.string().trim().max(300),
  active: z.boolean(),
  origins: z.array(z.string()).max(MAX_ALLOWED_ORIGINS, t('apiService.service.originsMax', { n: MAX_ALLOWED_ORIGINS })),
})
const state = reactive({ name: '', description: '', active: true, origins: [] as string[] })
// Allowed websites (leftovers L6): each one checked and put in its one form as it is added
const originError = ref<string | null>(null)
function setOrigins(values: string[]) {
  originError.value = null
  const out: string[] = []
  for (const value of values) {
    const origin = normaliseOrigin(value)
    if (!origin) originError.value = t('apiService.service.originInvalid', { value })
    else if (!out.includes(origin)) out.push(origin)
  }
  state.origins = out
}
const step = ref(0)
const created = ref<ApiService | null>(null)
watch(open, value => {
  if (!value) return
  state.name = props.service?.name ?? ''
  state.description = props.service?.description ?? ''
  state.active = (props.service?.status ?? 'active') === 'active'
  state.origins = [...(props.service?.allowed_origins ?? [])]
  originError.value = null
  created.value = null
  step.value = props.service ? 1 : 0
}, { immediate: true })
const steps = computed(() => [
  { title: t('apiService.service.steps.about'), icon: 'i-lucide-info' },
  { title: t('apiService.service.steps.details'), icon: 'i-lucide-pencil' },
  { title: t('apiService.service.steps.next'), icon: 'i-lucide-arrow-right' },
].map((item, i) => ({ ...item, value: i + 1 })))
const form = useTemplateRef<{ setErrors: (errors: { name: string; message: string }[]) => void; submit: () => void }>('form')
const saving = ref(false)
async function submit(event: FormSubmitEvent<z.infer<typeof schema>>) {
  if (saving.value) return
  saving.value = true
  try {
    const body: ApiServiceSaveRequest = { name: event.data.name, description: event.data.description || null, status: event.data.active ? 'active' : 'disabled', allowed_origins: event.data.origins }
    const { data } = props.service ? await api.patch<ApiService>(`/api-services/${props.service.id}`, body) : await api.post<ApiService>('/api-services', body)
    emit('saved', data)
    void setup.refresh()
    if (props.service || !props.next) open.value = false
    else {
      created.value = data
      step.value = 2
    }
  } catch (error) {
    const normalised = handle(error, { silent: true })
    if (normalised.code === 'FRM-API-1003') form.value?.setErrors([{ name: 'name', message: t('errors.FRM-API-1003') }])
    else handle(error)
  } finally {
    saving.value = false
  }
}
const points = ['group', 'switch', 'watch'] as const
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="service ? t('apiService.service.editTitle') : t('apiService.service.newTitle')" :description="service ? t('apiService.service.desc') : undefined" :ui="{ content: 'sm:max-w-xl' }">
    <template #body>
      <div class="flex flex-col gap-5">
        <UStepper v-if="!service" :model-value="step + 1" :items="steps" :linear="true" disabled color="neutral" size="xs" class="w-full" />

        <!-- 1 · What a service is -->
        <div v-if="step === 0" class="flex flex-col gap-4">
          <div class="flex items-center justify-center gap-2 rounded-lg border border-dashed border-default bg-elevated/30 p-4" aria-hidden="true">
            <span class="flex flex-col items-center gap-1 text-xs text-muted"><UIcon name="i-lucide-smartphone" class="size-6 text-highlighted" />{{ t('apiService.service.about.app') }}</span>
            <UIcon name="i-lucide-arrow-right" class="size-4 text-muted" />
            <span class="flex flex-col items-center gap-1 rounded-lg bg-inverted px-3 py-2 text-xs font-medium text-inverted"><UIcon name="i-lucide-boxes" class="size-6" />{{ t('apiService.service.about.service') }}</span>
            <UIcon name="i-lucide-arrow-right" class="size-4 text-muted" />
            <span class="flex flex-col gap-1">
              <span v-for="n in 3" :key="n" class="rounded-md border border-default px-2 py-0.5 font-mono text-[11px] text-highlighted">/{{ t(`apiService.service.about.endpoint${n}`) }}</span>
            </span>
          </div>
          <p class="text-sm text-default">{{ t('apiService.service.about.text') }}</p>
          <ul class="flex flex-col gap-2">
            <li v-for="point in points" :key="point" class="flex items-start gap-2 text-sm text-muted">
              <UIcon name="i-lucide-check" class="mt-0.5 size-4 shrink-0 text-highlighted" />{{ t(`apiService.service.about.${point}`) }}
            </li>
          </ul>
          <div class="flex flex-col gap-2">
            <span class="text-xs font-medium tracking-wide text-muted uppercase">{{ t('apiService.journey.title') }}</span>
            <ApiJourney :summary="setup.summary.value" focus="service" compact :actions="false" />
          </div>
        </div>

        <!-- 2 · Details -->
        <UForm v-show="step === 1" id="api-service-form" ref="form" :schema="schema" :state="state" class="flex flex-col gap-4" @submit="submit">
          <UFormField name="name" :label="t('apiService.service.name')" :hint="`${state.name.length}/80`" :help="t('apiService.service.nameHelp')" required>
            <UInput v-model="state.name" :placeholder="t('apiService.service.namePlaceholder')" class="w-full" maxlength="80" />
          </UFormField>
          <UFormField name="description" :label="t('apiService.service.description')" :hint="t('apiService.optional')">
            <UTextarea v-model="state.description" :rows="3" autoresize class="w-full" maxlength="300" :placeholder="t('apiService.service.descriptionPlaceholder')" />
          </UFormField>
          <UFormField name="origins" :label="t('apiService.service.origins')" :hint="t('apiService.optional')" :help="originError ? undefined : t('apiService.service.originsHelp')" :error="originError ?? undefined">
            <UInputTags :model-value="state.origins" :placeholder="t('apiService.service.originsPlaceholder')" icon="i-lucide-globe" class="w-full" :max="MAX_ALLOWED_ORIGINS" @update:model-value="value => setOrigins(value as string[])" />
          </UFormField>
          <UFormField name="active">
            <USwitch v-model="state.active" :label="t('apiService.service.active')" :description="t('apiService.service.activeHint')" />
          </UFormField>
        </UForm>

        <!-- 3 · Created, what comes next -->
        <div v-if="step === 2 && created" class="flex flex-col gap-4">
          <div class="flex items-start gap-3 rounded-lg border border-default p-4">
            <span class="flex size-10 shrink-0 items-center justify-center rounded-full bg-inverted text-inverted"><UIcon name="i-lucide-check" class="size-5" /></span>
            <div class="flex min-w-0 flex-col gap-1">
              <span class="font-semibold text-highlighted">{{ t('apiService.service.done.title', { name: created.name }) }}</span>
              <span class="text-sm text-muted">{{ t('apiService.service.done.text') }}</span>
            </div>
          </div>
          <div class="flex flex-col gap-2 rounded-lg bg-elevated/40 p-4">
            <span class="flex items-center gap-2 text-sm font-semibold text-highlighted"><UIcon name="i-lucide-route" class="size-4" />{{ t('apiService.service.done.nextTitle') }}</span>
            <p class="text-sm text-muted">{{ t('apiService.service.done.nextText') }}</p>
          </div>
          <ApiJourney :summary="setup.summary.value" focus="endpoint" compact :actions="false" />
        </div>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full flex-wrap justify-end gap-2">
        <template v-if="step === 0">
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
          <UButton :label="t('apiService.service.steps.continue')" trailing-icon="i-lucide-arrow-right" color="neutral" @click="step = 1" />
        </template>
        <template v-else-if="step === 1">
          <UButton v-if="!service" :label="t('apiService.service.steps.back')" icon="i-lucide-arrow-left" color="neutral" variant="ghost" class="me-auto" @click="step = 0" />
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
          <UButton type="submit" form="api-service-form" :label="service ? t('common.save') : t('apiService.service.create')" color="neutral" :loading="saving" />
        </template>
        <template v-else>
          <UButton :label="t('apiService.service.done.later')" color="neutral" variant="outline" @click="open = false" />
          <UButton v-if="can('api.endpoints')" :label="t('apiService.service.done.endpoint')" icon="i-lucide-plus" color="neutral" :to="{ path: '/api-service/endpoints/new', query: { service: created?.id } }" @click="open = false" />
        </template>
      </div>
    </template>
  </AppModal>
</template>
