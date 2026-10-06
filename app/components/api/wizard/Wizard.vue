<!--
  New / edit endpoint (F13 M1), step by step: form → name and service → methods → questions →
  review. Each step is checked before moving on (the same checks run on the server). The address
  and an example call update beside it as you go (below on phones). Editing: every step is one
  click away; picking another form starts its questions afresh.
-->
<script setup lang="ts">
import type { ApiEndpointDetail, ApiEndpointField, ApiEndpointSaveRequest, ApiHeaderDraft, ApiServiceSettings, ApiStatus } from '#shared/types/apiService'
import { checkEndpointName, endpointNameFrom } from '#shared/utils/apiService/endpoints'
import { checkHeaderName, checkHeaderValue } from '#shared/utils/apiService/tokens'
import type { ApiMethod } from '#shared/utils/urls/public'

const props = defineProps<{ endpoint?: ApiEndpointDetail | null; service?: string | null }>()
const emit = defineEmits<{ saved: [endpoint: ApiEndpointDetail]; dirty: [value: boolean] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const setup = useApiSetup()

const STEPS = ['form', 'basics', 'methods', 'fields', 'review'] as const
type Step = (typeof STEPS)[number]
const ICONS: Record<Step, string> = { form: 'i-lucide-file-text', basics: 'i-lucide-route', methods: 'i-lucide-arrow-left-right', fields: 'i-lucide-list-checks', review: 'i-lucide-circle-check' }
const editing = computed(() => !!props.endpoint)
const current = ref<Step>(editing.value ? 'basics' : 'form')
const index = computed(() => STEPS.indexOf(current.value))

const e = props.endpoint
const formId = ref<string | null>(e?.form.id ?? null)
const formName = ref(e?.form.name ?? '')
const serviceId = ref<string | null>(e?.service.id ?? props.service ?? null)
const name = ref(e?.name ?? '')
const description = ref(e?.description ?? '')
const version = ref<number | null>(e?.version ?? null)
const methods = ref<ApiMethod[]>(e ? [...e.methods] : ['POST'])
const pageSize = ref(e?.page_size ?? 50)
const status = ref<ApiStatus>(e?.status ?? 'disabled')
const fields = ref<ApiEndpointField[]>(e ? e.fields.map(field => ({ ...field })) : [])
const versions = ref<number[]>(e?.versions ?? [])
const headers = ref<ApiHeaderDraft[]>((e?.headers ?? []).map(header => ({ name: header.name, value: null, preview: header.preview })))
const headerErrors = ref(false)
const errors = ref<Record<string, string>>({})

const snapshot = () => JSON.stringify([formId.value, serviceId.value, name.value, description.value, version.value, methods.value, pageSize.value, status.value, headers.value, fields.value.map(f => [f.key, f.accept, f.required, f.returned, f.filter])])
const initial = ref(snapshot())
watch(() => snapshot() !== initial.value, value => emit('dirty', value), { immediate: true })

const settings = ref<ApiServiceSettings | null>(null)
onMounted(async () => {
  try {
    settings.value = (await api.get<ApiServiceSettings>('/api-service/settings', undefined, { background: true })).data
  } catch {
    settings.value = null
  }
})
const base = computed(() => (settings.value ? `${settings.value.base_url}/${settings.value.api_key}` : '…'))
const url = computed(() => `${base.value}/${name.value || 'endpoint-name'}`)

// The form's questions (on picking a form or a version; ticks carry over by key)
const loadingFields = ref(false)
async function loadFields() {
  if (!formId.value) return
  loadingFields.value = true
  try {
    const { data } = await api.get<{ fields: ApiEndpointField[]; versions: number[] }>('/api-endpoints/form-fields', { form_id: formId.value, ...(version.value ? { version: version.value } : {}) })
    const before = new Map(fields.value.map(field => [field.key, field]))
    fields.value = data.fields.map(field => {
      const own = before.get(field.key)
      if (!own) return field
      const accept = field.acceptable && (field.form_required || own.accept)
      return { ...field, accept, required: accept && (field.form_required || own.required), returned: own.returned, filter: field.filterable && own.returned && own.filter }
    })
    versions.value = data.versions
  } catch (error) {
    handle(error)
  } finally {
    loadingFields.value = false
  }
}
function picked(form: { id: string; name: string }) {
  if (form.name !== formName.value) {
    fields.value = []
    version.value = null
  }
  formName.value = form.name
  if (!name.value) name.value = endpointNameFrom(form.name)
  void loadFields()
}
watch(version, () => void loadFields())
const changeField = (key: string, patch: Partial<ApiEndpointField>) => (fields.value = fields.value.map(field => (field.key === key ? { ...field, ...patch } : field)))
const writes = computed(() => methods.value.some(method => method === 'POST' || method === 'PUT'))
const reads = computed(() => methods.value.includes('GET'))

function check(step: Step): boolean {
  const problems: Record<string, string> = {}
  if (step === 'form' && !formId.value) problems.form = t('apiService.invalid.form')
  if (step === 'basics') {
    if (!serviceId.value) problems.service_id = t('apiService.invalid.required')
    const problem = checkEndpointName(name.value)
    if (problem) problems.name = t(`apiService.invalid.${problem}`)
  }
  if (step === 'methods' && !methods.value.length) problems.methods = t('apiService.invalid.methods')
  if (step === 'methods') {
    const names = headers.value.map(header => header.name.trim().toLowerCase())
    const bad = headers.value.some((header, i) => checkHeaderName(header.name.trim()) || names.indexOf(names[i]!) !== i || (header.value === null ? !header.preview : checkHeaderValue(header.value)))
    headerErrors.value = bad
    if (bad) problems.headers = t('apiService.headers.invalid.fix')
  }
  if (step === 'fields') {
    if (writes.value && !fields.value.some(field => field.accept)) problems.fields = t('apiService.invalid.accept')
    else if (reads.value && !fields.value.some(field => field.returned)) problems.fields = t('apiService.invalid.returned')
  }
  errors.value = problems
  return !Object.keys(problems).length
}
function go(target: Step) {
  const to = STEPS.indexOf(target)
  for (let i = index.value; i < to; i++) {
    if (!check(STEPS[i]!)) return void (current.value = STEPS[i]!)
  }
  errors.value = {}
  current.value = target
}
const next = () => index.value < STEPS.length - 1 && go(STEPS[index.value + 1]!)
const back = () => index.value > 0 && go(STEPS[index.value - 1]!)
const stepItems = computed(() => STEPS.map((step, i) => ({ value: step, title: t(`apiService.wizard.step.${step}`), icon: ICONS[step], disabled: !editing.value && i > index.value + 1 })))

const saving = ref(false)
async function save() {
  for (const step of STEPS.slice(0, -1)) if (!check(step)) return void (current.value = step)
  saving.value = true
  try {
    const body: ApiEndpointSaveRequest = {
      name: name.value,
      description: description.value.trim() || null,
      service_id: serviceId.value!,
      form_id: formId.value!,
      version: version.value,
      methods: methods.value,
      fields: fields.value.map(({ key, accept, required, returned, filter }) => ({ key, accept, required, returned, filter })),
      page_size: pageSize.value,
      headers: headers.value.map(header => ({ name: header.name.trim(), value: header.value })),
      status: status.value,
    }
    const { data } = props.endpoint ? await api.patch<ApiEndpointDetail>(`/api-endpoints/${props.endpoint.id}`, body) : await api.post<ApiEndpointDetail>('/api-endpoints', body)
    initial.value = snapshot()
    emit('saved', data)
  } catch (error) {
    const normalised = handle(error)
    if (normalised.code === 'FRM-API-1001') {
      errors.value = { name: t('errors.FRM-API-1001') }
      current.value = 'basics'
    }
  } finally {
    saving.value = false
  }
}
defineShortcuts({ meta_enter: { usingInput: true, handler: () => (current.value === 'review' ? void save() : next()) } })
</script>

<template>
  <div class="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_20rem] xl:grid-cols-[minmax(0,1fr)_24rem]">
    <UCard variant="outline" class="min-w-0" :ui="{ header: 'flex flex-col gap-4 p-4 sm:p-5', body: 'p-4 sm:p-5', footer: 'flex items-center justify-between gap-2 p-4 sm:px-5' }">
      <template #header>
        <UStepper :model-value="current" :items="stepItems" size="xs" color="neutral" :linear="false" class="w-full" :ui="{ title: 'hidden md:block text-xs', description: 'hidden' }" @update:model-value="value => go(value as Step)" />
        <div class="flex flex-col">
          <p class="text-xs text-muted">{{ t('apiService.wizard.stepOf', { n: index + 1, total: STEPS.length }) }}</p>
          <h2 class="text-base font-semibold text-highlighted">{{ t(`apiService.wizard.title.${current}`) }}</h2>
          <p class="text-sm text-muted">{{ t(`apiService.wizard.desc.${current}`) }}</p>
        </div>
      </template>

      <div v-if="current === 'form'" class="flex flex-col gap-2">
        <ApiWizardForm v-model:form-id="formId" @picked="picked" />
        <p v-if="errors.form" class="text-sm text-error">{{ errors.form }}</p>
      </div>
      <ApiWizardBasics v-else-if="current === 'basics'" v-model:service-id="serviceId" v-model:name="name" v-model:description="description" v-model:version="version" :base="base" :versions="versions" :errors="errors" />
      <div v-else-if="current === 'methods'" class="flex flex-col gap-5">
        <ApiWizardMethods v-model:methods="methods" v-model:page-size="pageSize" :error="errors.methods" />
        <ApiWizardHeaders v-model="headers" :show-errors="headerErrors" />
      </div>
      <div v-else-if="current === 'fields'" class="flex flex-col gap-3">
        <div v-if="loadingFields && !fields.length" class="flex flex-col gap-2"><USkeleton v-for="n in 5" :key="n" class="h-12 w-full" /></div>
        <ApiEndpointsFields v-else :fields="fields" editable :writes="writes" :reads="reads" :class="loadingFields ? 'opacity-60' : ''" @change="changeField" />
        <p v-if="errors.fields" class="text-sm text-error">{{ errors.fields }}</p>
      </div>
      <div v-else class="flex flex-col gap-5">
        <dl class="grid gap-x-6 gap-y-3 sm:grid-cols-2">
          <div class="flex min-w-0 flex-col"><dt class="text-xs text-muted">{{ t('apiService.wizard.step.form') }}</dt><dd class="truncate text-sm font-medium text-highlighted">{{ formName }}</dd></div>
          <div class="flex min-w-0 flex-col"><dt class="text-xs text-muted">{{ t('apiService.col.version') }}</dt><dd class="text-sm font-medium text-highlighted">{{ version ? t('apiService.versionN', { n: version }) : t('apiService.latestVersion') }}</dd></div>
          <div class="flex min-w-0 flex-col"><dt class="text-xs text-muted">{{ t('apiService.col.methods') }}</dt><dd><ApiMethods :methods="methods" size="xs" /></dd></div>
          <div class="flex min-w-0 flex-col"><dt class="text-xs text-muted">{{ t('apiService.fields.title') }}</dt><dd class="text-sm text-highlighted">{{ t('apiService.wizard.fieldsSummary', { accepted: fields.filter(f => f.accept).length, returned: fields.filter(f => f.returned).length }) }}</dd></div>
        </dl>
        <USwitch v-if="editing" :model-value="status === 'active'" :label="t('apiService.setup.isLive')" :description="t('apiService.wizard.answeringHint')" @update:model-value="value => (status = value ? 'active' : 'disabled')" />
        <div v-else class="flex flex-col gap-3 rounded-lg bg-elevated/40 p-4">
          <span class="flex items-center gap-2 text-sm font-semibold text-highlighted"><UIcon name="i-lucide-flag" class="size-4" />{{ t('apiService.wizard.afterTitle') }}</span>
          <p class="text-sm text-muted">{{ t('apiService.wizard.afterText') }}</p>
          <ApiJourney :summary="setup.summary.value" focus="token" compact :actions="false" />
        </div>
      </div>

      <template #footer>
        <UButton :label="t('apiService.wizard.back')" icon="i-lucide-arrow-left" color="neutral" variant="ghost" :disabled="index === 0" class="rtl:[&_.iconify]:-scale-x-100" @click="back" />
        <UButton v-if="current !== 'review'" :label="t('apiService.wizard.next')" trailing-icon="i-lucide-arrow-right" color="neutral" class="rtl:[&_.iconify]:-scale-x-100" @click="next" />
        <UButton v-else :label="editing ? t('common.save') : t('apiService.wizard.create')" icon="i-lucide-check" color="neutral" :loading="saving" @click="save" />
      </template>
    </UCard>

    <ApiWizardAside :url="url" :methods="methods" :fields="fields" :page-size="pageSize" :form-name="formName" :headers="headers.filter(header => header.name).map(header => ({ name: header.name, value: header.value || header.preview || '…' }))" />
  </div>
</template>
