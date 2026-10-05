<!--
  One step of a connection's settings, drawn from the engine catalogue
  (shared/utils/datasources/engines.ts): text, numbers, choices, switches, secrets (write-only:
  a saved one shows "Saved, leave empty to keep") and certificates (paste, or read from a file
  on this device; nothing is uploaded until Save). Rarely needed fields sit under More options.
-->
<script setup lang="ts">
import type { DataSourceSecrets, DataSourceSettings, DbEngine } from '#shared/types/datasources'
import { fieldsFor, isSecretField, type EngineField, type FieldStep } from '#shared/utils/datasources/engines'

const props = defineProps<{ engine: DbEngine; step: FieldStep; secretsSet?: string[]; errors: Record<string, string> }>()
const settings = defineModel<DataSourceSettings>('settings', { required: true })
const secrets = defineModel<DataSourceSecrets>('secrets', { required: true })
const { t, te } = useI18n()

const fields = computed(() => fieldsFor(props.engine, settings.value, props.step))
const basic = computed(() => fields.value.filter(field => !field.advanced))
const advanced = computed(() => fields.value.filter(field => field.advanced))
const moreOpen = ref(false)
// A problem inside More options opens it.
watch(() => props.errors, errors => advanced.value.some(field => errors[field.key]) && (moreOpen.value = true))

const label = (field: EngineField) => t(`dataSources.field.${field.key}`)
const hint = (field: EngineField) => (te(`dataSources.hint.${props.engine}.${field.key}`) ? t(`dataSources.hint.${props.engine}.${field.key}`) : te(`dataSources.hint.${field.key}`) ? t(`dataSources.hint.${field.key}`) : undefined)
const error = (field: EngineField) => (props.errors[field.key] ? t(`dataSources.invalid.${props.errors[field.key]}`) : undefined)
const items = (field: EngineField) => (field.options ?? []).map(value => ({ value, label: t(`dataSources.option.${field.key}.${value}`) }))
const isSaved = (field: EngineField) => isSecretField(field) && !!props.secretsSet?.includes(field.key)

function setValue(field: EngineField, value: unknown) {
  if (isSecretField(field)) secrets.value = { ...secrets.value, [field.key]: String(value ?? '') }
  else settings.value = { ...settings.value, [field.key]: field.type === 'number' ? (value === '' || value === null ? '' : Number(value)) : (value as string | boolean) }
}
const valueOf = (field: EngineField) => (isSecretField(field) ? (secrets.value[field.key] ?? '') : settings.value[field.key])

const shown = ref<Record<string, boolean>>({})
const bind = (field: EngineField) => ({ field, label: label(field), hint: hint(field), error: error(field), items: items(field), saved: isSaved(field), value: valueOf(field), shown: !!shown.value[field.key] })

// Certificates and keys: read a file on this device into the box.
const reading = ref<string | null>(null)
const { open: openFile, onChange } = useFileDialog({ accept: '.pem,.crt,.cer,.key,.txt', multiple: false, reset: true })
onChange(async files => {
  const file = files?.[0]
  const key = reading.value
  if (!file || !key || file.size > 64_000) return
  secrets.value = { ...secrets.value, [key]: await file.text() }
})
function pickFile(field: EngineField) {
  reading.value = field.key
  openFile()
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <DatasourcesWizardField v-for="field in basic" :key="field.key" v-bind="bind(field)" @update="value => setValue(field, value)" @toggle="shown[field.key] = !shown[field.key]" @file="pickFile(field)" />
    </div>
    <UCollapsible v-if="advanced.length" v-model:open="moreOpen" class="flex flex-col gap-4">
      <UButton :label="t('dataSources.moreOptions')" :trailing-icon="moreOpen ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'" color="neutral" variant="link" size="sm" class="w-fit px-0" />
      <template #content>
        <div class="grid grid-cols-1 gap-4 pt-1 sm:grid-cols-2">
          <DatasourcesWizardField v-for="field in advanced" :key="field.key" v-bind="bind(field)" @update="value => setValue(field, value)" @toggle="shown[field.key] = !shown[field.key]" @file="pickFile(field)" />
        </div>
      </template>
    </UCollapsible>
  </div>
</template>
