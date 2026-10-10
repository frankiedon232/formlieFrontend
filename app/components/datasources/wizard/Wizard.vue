<!--
  Add / edit a connection (F12 M1), step by step: database → server → sign in → security →
  access → name and test. Each step only shows this engine's own settings and is checked before
  moving on (the same checks run on the server). The test runs from Formalie's servers and never
  changes data; Save takes its result as the connection's status. A failed test can still be
  saved after a confirm (it shows as failing). Editing: the engine stays, every step is one
  click away, secrets left empty keep the saved ones, and only a renamed connection skips the test.
-->
<script setup lang="ts">
import type { DataSourceAccessSettings, DataSourceDetail, DataSourceSaveRequest, DataSourceSecrets, DataSourceSettings } from '#shared/types/datasources'
import type { DbEngine } from '#shared/utils/integrations/databases'
import { checkConfig, cleanSecrets, databaseNameOf, defaultSettings, type FieldStep } from '#shared/utils/datasources/engines'
import { DEFAULT_ACCESS } from '#shared/utils/datasources/permissions'

const props = defineProps<{ source?: DataSourceDetail | null }>()
const emit = defineEmits<{ saved: [source: DataSourceDetail]; dirty: [value: boolean] }>()
const { t } = useI18n()
const api = useApi()
const confirm = useConfirm()
const { handle } = useErrorHandler()

const ALL = ['engine', 'server', 'signin', 'security', 'access', 'review'] as const
type Step = (typeof ALL)[number]
const ICONS: Record<Step, string> = { engine: 'i-lucide-database', server: 'i-lucide-server', signin: 'i-lucide-user-round', security: 'i-lucide-lock', access: 'i-lucide-key-round', review: 'i-lucide-activity' }
const editing = computed(() => !!props.source)
// A role that may only see this connection walks the steps but cannot save (the server refuses too)
const readOnly = computed(() => !!props.source && !props.source.can?.edit)
const steps = computed<Step[]>(() => (editing.value ? ALL.slice(1) : [...ALL]))
const current = ref<Step>(steps.value[0]!)
const index = computed(() => steps.value.indexOf(current.value))

const engine = ref<DbEngine | null>(props.source?.engine ?? null)
const settings = ref<DataSourceSettings>(props.source ? { ...props.source.settings } : {})
const secrets = ref<DataSourceSecrets>({})
const access = ref<DataSourceAccessSettings>(props.source ? { ...props.source.access, schemas: [...props.source.access.schemas] } : { ...DEFAULT_ACCESS })
const name = ref(props.source?.name ?? '')
const secretsSet = computed(() => props.source?.secrets_set ?? [])
const errors = ref<Record<string, string>>({})
const nameError = ref<string>()

// A different database keeps what carries over (host, database, account) and takes its defaults.
watch(engine, (value, old) => {
  if (!value || value === old || editing.value) return
  const keep = Object.fromEntries(['host', 'database', 'username'].filter(key => settings.value[key]).map(key => [key, settings.value[key]!]))
  settings.value = { ...defaultSettings(value), ...keep }
  secrets.value = {}
})

const config = computed(() => JSON.stringify([engine.value, settings.value, secrets.value, access.value]))
const initial = ref(JSON.stringify([engine.value, settings.value, {}, access.value, name.value]))
const dirty = computed(() => JSON.stringify([engine.value, settings.value, secrets.value, access.value, name.value]) !== initial.value)
watch(dirty, value => emit('dirty', value), { immediate: true })

const runner = useConnectionTest()
watch(config, () => runner.test.value && runner.reset())
const configChanged = computed(() => !editing.value || config.value !== JSON.stringify([props.source!.engine, props.source!.settings, {}, props.source!.access]))

function check(step: Step): boolean {
  if (step === 'engine') return !!engine.value
  if (step === 'server' || step === 'signin' || step === 'security') {
    const problems = checkConfig(engine.value!, settings.value, secrets.value, secretsSet.value, step as FieldStep)
    errors.value = { ...problems }
    return !Object.keys(problems).length
  }
  if (step === 'review') {
    nameError.value = name.value.trim() ? undefined : t('dataSources.invalid.required')
    return !nameError.value
  }
  return true
}

/** Moving forward checks every step on the way; moving back never does. */
function go(target: Step) {
  const to = steps.value.indexOf(target)
  for (let i = index.value; i < to; i++) {
    if (!check(steps.value[i]!)) {
      current.value = steps.value[i]!
      return
    }
  }
  errors.value = {}
  current.value = target
  if (target === 'review' && !name.value.trim() && engine.value) name.value = databaseNameOf(engine.value, settings.value) || engineName(engine.value)
}
const next = () => index.value < steps.value.length - 1 && go(steps.value[index.value + 1]!)
const back = () => index.value > 0 && go(steps.value[index.value - 1]!)

const stepItems = computed(() => steps.value.map((step, i) => ({ value: step, title: t(`dataSources.wizard.step.${step}`), icon: ICONS[step], disabled: !editing.value && i > index.value + 1 })))

function request() {
  return { engine: engine.value!, settings: settings.value, access: access.value, secrets: cleanSecrets(engine.value!, settings.value, secrets.value) }
}
async function runTest() {
  if (!['server', 'signin', 'security'].every(step => check(step as Step))) {
    const failing = (['server', 'signin', 'security'] as Step[]).find(step => !check(step))
    if (failing) current.value = failing
    return
  }
  await runner.start({ ...request(), datasource_id: props.source?.id })
}

const saving = ref(false)
async function save() {
  if (readOnly.value || !check('review')) return
  const test = runner.test.value
  if (configChanged.value) {
    if (!test || test.status === 'running') return void runTest()
    if (test.status === 'failed' && !(await confirm({ title: t('dataSources.wizard.saveFailedTitle'), description: t('dataSources.wizard.saveFailedDesc'), confirmLabel: t('dataSources.wizard.saveAnyway') }))) return
  }
  saving.value = true
  try {
    const body: DataSourceSaveRequest = { ...request(), name: name.value.trim(), test_id: configChanged.value ? test?.id : undefined }
    const { data } = props.source
      ? await api.patch<DataSourceDetail>(`/datasources/${props.source.id}`, { name: body.name, ...(configChanged.value ? { settings: body.settings, access: body.access, secrets: body.secrets, test_id: body.test_id } : {}) })
      : await api.post<DataSourceDetail>('/datasources', body)
    initial.value = JSON.stringify([engine.value, settings.value, secrets.value, access.value, name.value])
    emit('saved', data)
  } catch (error) {
    const normalised = handle(error)
    if (normalised.code === 'FRM-DEST-1007') nameError.value = t('errors.FRM-DEST-1007')
  } finally {
    saving.value = false
  }
}
const saveLabel = computed(() => {
  const test = runner.test.value
  if (configChanged.value && (!test || test.status === 'running')) return t('dataSources.wizard.testAndSave')
  return test?.status === 'failed' && configChanged.value ? t('dataSources.wizard.saveAnyway') : props.source ? t('common.save') : t('dataSources.wizard.save')
})
</script>

<template>
  <div class="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_20rem] xl:grid-cols-[minmax(0,1fr)_22rem]">
    <UCard variant="outline" :ui="{ header: 'flex flex-col gap-4 p-4 sm:p-5', body: 'p-4 sm:p-5', footer: 'flex items-center justify-between gap-2 p-4 sm:px-5' }">
      <template #header>
        <UStepper :model-value="current" :items="stepItems" size="xs" color="neutral" :linear="false" class="w-full" :ui="{ title: 'hidden md:block text-xs', description: 'hidden' }" @update:model-value="value => go(value as Step)" />
        <div class="flex flex-col">
          <p class="text-xs text-muted">{{ t('dataSources.wizard.stepOf', { n: index + 1, total: steps.length }) }}</p>
          <h2 class="text-base font-semibold text-highlighted">{{ t(`dataSources.wizard.title.${current}`) }}</h2>
          <p class="text-sm text-muted">{{ t(`dataSources.wizard.desc.${current}`, { engine: engine ? engineName(engine) : '' }) }}</p>
        </div>
      </template>

      <form id="connection-step" novalidate @submit.prevent="current === 'review' ? save() : next()">
        <DatasourcesWizardEngine v-if="current === 'engine'" v-model="engine" />
        <DatasourcesWizardFields v-else-if="engine && (current === 'server' || current === 'signin' || current === 'security')" :key="current" v-model:settings="settings" v-model:secrets="secrets" :engine="engine" :step="current" :secrets-set="secretsSet" :errors="errors" />
        <DatasourcesWizardAccess v-else-if="engine && current === 'access'" v-model="access" :engine="engine" :settings="settings" />
        <DatasourcesWizardReview v-else-if="engine && current === 'review'" v-model:name="name" :engine="engine" :settings="settings" :access="access" :test="runner.test.value" :starting="runner.starting.value" :running="runner.running.value" :name-error="nameError" @test="runTest" @jump="step => go(step as Step)" />
      </form>

      <template #footer>
        <UButton :label="t('common.back')" icon="i-lucide-arrow-left" color="neutral" variant="outline" :disabled="index === 0 || saving" class="rtl:[&_.iconify]:-scale-x-100" @click="back" />
        <UButton
          v-if="current !== 'review'"
          type="submit"
          form="connection-step"
          :label="t('common.next')"
          trailing-icon="i-lucide-arrow-right"
          color="neutral"
          :disabled="current === 'engine' && !engine"
          class="rtl:[&_.iconify]:-scale-x-100"
        />
        <UButton v-else-if="!readOnly" type="submit" form="connection-step" :label="saveLabel" icon="i-lucide-check" color="neutral" :loading="saving || runner.starting.value || runner.running.value" />
      </template>
    </UCard>

    <DatasourcesWizardAside :step="current" :engine="engine" />
  </div>
</template>
