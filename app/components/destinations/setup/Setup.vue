<!--
  Store a form's responses in a database (F12 M2), step by step: connection → table → columns →
  options → review. Each step is checked before moving on (the server checks again). Saving
  creates the table (or adds what an existing table needs) and starts delivering new responses;
  changing a set-up destination opens at the columns, the connection and table stay.
-->
<script setup lang="ts">
import type { DestinationDetail, StorageField  } from '#shared/types/destinations'
import { blocking } from '#shared/utils/datasources/tables'

const props = defineProps<{ formId: string; formName: string; fields: StorageField[]; destination?: DestinationDetail | null }>()
const emit = defineEmits<{ saved: [destination: DestinationDetail, created: boolean]; dirty: [value: boolean] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()

const ALL = ['connection', 'table', 'columns', 'options', 'review'] as const
type Step = (typeof ALL)[number]
const ICONS: Record<Step, string> = { connection: 'i-lucide-database', table: 'i-lucide-table-2', columns: 'i-lucide-columns-3', options: 'i-lucide-sliders-horizontal', review: 'i-lucide-circle-check' }
const editing = computed(() => !!props.destination)
const steps = computed<Step[]>(() => (editing.value ? ['columns', 'options', 'review'] : [...ALL]))
const current = ref<Step>(steps.value[0]!)
const index = computed(() => steps.value.indexOf(current.value))

const setup = useStorageSetup({ formName: () => props.formName, fields: () => props.fields, destination: props.destination })
const nameError = ref<string>()
const touched = ref(false)
watch([setup.sourceId, setup.tableName, setup.existingKey, setup.settings, setup.manual, setup.renames, setup.skipped, setup.extraMeta], () => (touched.value = true), { deep: true })
watch(touched, value => emit('dirty', value))

function check(step: Step): boolean {
  nameError.value = undefined
  if (step === 'connection') return !!setup.source.value && setup.source.value.id === setup.sourceId.value
  if (step === 'table') {
    if (setup.mode.value === 'existing') {
      if (!setup.existing.value) nameError.value = t('dataSources.invalid.required')
      return !!setup.existing.value
    }
    const name = setup.tableName.value.trim()
    if (!name) nameError.value = t('dataSources.invalid.required')
    else if (!name.startsWith(setup.prefix.value)) nameError.value = t('destinations.setup.mustStartWith', { prefix: setup.prefix.value })
    else if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) nameError.value = t('destinations.setup.nameChars')
    else if (setup.nameTaken.value) nameError.value = t('errors.FRM-DEST-1014')
    return !nameError.value
  }
  if (step === 'columns' || step === 'options') return !blocking(setup.issues.value).length
  return true
}
function go(target: Step) {
  const to = steps.value.indexOf(target)
  for (let i = index.value; i < to; i++) {
    if (!check(steps.value[i]!)) {
      current.value = steps.value[i]!
      return
    }
  }
  current.value = target
}
const next = () => index.value < steps.value.length - 1 && go(steps.value[index.value + 1]!)
const back = () => index.value > 0 && go(steps.value[index.value - 1]!)
const stepItems = computed(() => steps.value.map((step, i) => ({ value: step, title: t(`destinations.setup.step.${step}`), icon: ICONS[step], disabled: !editing.value && i > index.value + 1 })))

const saving = ref(false)
async function save() {
  if (!steps.value.every(step => check(step))) return void go('review')
  saving.value = true
  try {
    const columns = setup.columns.value
    const { data } = props.destination
      ? await api.patch<DestinationDetail>(`/destinations/${props.destination.id}`, { settings: setup.settings.value, columns })
      : await api.post<DestinationDetail>('/destinations', {
          form_id: props.formId,
          datasource_id: setup.sourceId.value,
          table: setup.mode.value === 'create' ? { mode: 'create', schema: setup.tablesSchema.value, name: setup.tableName.value.trim() } : { mode: 'existing', schema: setup.existing.value!.schema, name: setup.existing.value!.name },
          columns,
          settings: setup.settings.value,
        })
    touched.value = false
    emit('saved', data, !props.destination)
  } catch (error) {
    const normalised = handle(error)
    if (normalised.code === 'FRM-DEST-1014') {
      nameError.value = t('errors.FRM-DEST-1014')
      current.value = 'table'
    } else if (normalised.code === 'FRM-DEST-1016') current.value = 'columns'
  } finally {
    saving.value = false
  }
}
const saveLabel = computed(() => (editing.value ? t('common.save') : setup.mode.value === 'create' ? t('destinations.setup.createAndStart') : t('destinations.setup.start')))
</script>

<template>
  <div class="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_20rem] xl:grid-cols-[minmax(0,1fr)_22rem]">
    <UCard variant="outline" :ui="{ header: 'flex flex-col gap-4 p-4 sm:p-5', body: 'p-4 sm:p-5', footer: 'flex items-center justify-between gap-2 p-4 sm:px-5' }">
      <template #header>
        <UStepper :model-value="current" :items="stepItems" size="xs" color="neutral" :linear="false" class="w-full" :ui="{ title: 'hidden md:block text-xs', description: 'hidden' }" @update:model-value="value => go(value as Step)" />
        <div class="flex flex-col">
          <p class="text-xs text-muted">{{ t('dataSources.wizard.stepOf', { n: index + 1, total: steps.length }) }}</p>
          <h2 class="text-base font-semibold text-highlighted">{{ t(`destinations.setup.title.${current}`) }}</h2>
          <p class="text-sm text-muted">{{ t(`destinations.setup.desc.${current}`, { form: formName }) }}</p>
        </div>
      </template>

      <form id="storage-step" novalidate @submit.prevent="current === 'review' ? save() : next()">
        <DestinationsSetupConnection v-if="current === 'connection'" :setup="setup" />
        <DestinationsSetupTable v-else-if="current === 'table'" :setup="setup" :name-error="nameError" />
        <DestinationsSetupColumns v-else-if="current === 'columns'" :setup="setup" :fields="fields" :editing="editing" />
        <DestinationsSetupOptions v-else-if="current === 'options'" :setup="setup" :editing="editing" />
        <DestinationsSetupReview v-else :setup="setup" :editing="editing" @jump="step => go(step as Step)" />
      </form>

      <template #footer>
        <UButton :label="t('common.back')" icon="i-lucide-arrow-left" color="neutral" variant="outline" :disabled="index === 0 || saving" class="rtl:[&_.iconify]:-scale-x-100" @click="back" />
        <UButton v-if="current !== 'review'" type="submit" form="storage-step" :label="t('common.next')" trailing-icon="i-lucide-arrow-right" color="neutral" :disabled="current === 'connection' && !setup.source.value" :loading="setup.loadingTables.value && current === 'connection'" class="rtl:[&_.iconify]:-scale-x-100" />
        <UButton v-else type="submit" form="storage-step" :label="saveLabel" icon="i-lucide-check" color="neutral" :loading="saving" />
      </template>
    </UCard>

    <DestinationsSetupAside :step="current" />
  </div>
</template>
