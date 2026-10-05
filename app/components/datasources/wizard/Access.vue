<!--
  What Formalie may do on this database: read only (the safe default) or read + write, creating
  tables for form destinations (read + write only), and which schemas it uses. Below: every
  operation with the privilege behind it, and the statements to run, written for this connection.
-->
<script setup lang="ts">
import type { DataSourceAccessSettings, DataSourceSettings, DbEngine } from '#shared/types/datasources'
import { defaultSchemaOf } from '#shared/utils/datasources/engines'

const props = defineProps<{ engine: DbEngine; settings: DataSourceSettings }>()
const access = defineModel<DataSourceAccessSettings>({ required: true })
const { t } = useI18n()

const modes = computed(() => [
  { value: 'read_only', label: t('dataSources.access.read_only'), description: t('dataSources.access.readOnlyDesc') },
  { value: 'read_write', label: t('dataSources.access.read_write'), description: t('dataSources.access.readWriteDesc') },
])
const setMode = (mode: DataSourceAccessSettings['mode']) => (access.value = { ...access.value, mode, structure: mode === 'read_write' && access.value.structure })
const schemaHint = computed(() => t(props.engine === 'mysql' || props.engine === 'mariadb' ? 'dataSources.access.databasesHint' : 'dataSources.access.schemasHint', { schema: defaultSchemaOf(props.engine, props.settings) || '…' }))
const tab = ref('operations')
const tabs = computed(() => [
  { value: 'operations', label: t('dataSources.access.tabOperations'), icon: 'i-lucide-list-checks' },
  { value: 'script', label: t('dataSources.access.tabScript'), icon: 'i-lucide-square-terminal' },
])
</script>

<template>
  <div class="flex flex-col gap-5">
    <URadioGroup
      :model-value="access.mode"
      :items="modes"
      variant="card"
      indicator="end"
      color="neutral"
      :legend="t('dataSources.access.legend')"
      :ui="{ fieldset: 'grid grid-cols-1 gap-3 sm:grid-cols-2', legend: 'mb-2 text-sm font-medium text-highlighted', item: 'items-start has-data-[state=checked]:border-inverted' }"
      @update:model-value="value => setMode(value as DataSourceAccessSettings['mode'])"
    />
    <USwitch
      :model-value="access.structure"
      :disabled="access.mode !== 'read_write'"
      :label="t('dataSources.access.structure')"
      :description="t('dataSources.access.structureDesc')"
      @update:model-value="value => (access = { ...access, structure: !!value })"
    />
    <UFormField :label="engine === 'mysql' || engine === 'mariadb' ? t('dataSources.access.databases') : t('dataSources.access.schemas')" :description="schemaHint">
      <UInputTags :model-value="access.schemas" :max-length="128" class="w-full font-mono" dir="ltr" @update:model-value="value => (access = { ...access, schemas: (value as string[]).map(item => item.trim()).filter(Boolean).slice(0, 20) })" />
    </UFormField>

    <div class="flex flex-col gap-3 rounded-lg border border-default p-3 sm:p-4">
      <div class="flex items-start gap-2">
        <UIcon name="i-lucide-key-round" class="mt-0.5 size-4 shrink-0 text-highlighted" />
        <div class="flex flex-col">
          <h3 class="text-sm font-semibold text-highlighted">{{ t('dataSources.access.permissionsTitle') }}</h3>
          <p class="text-xs text-muted">{{ t('dataSources.access.permissionsDesc') }}</p>
        </div>
      </div>
      <UTabs v-model="tab" :items="tabs" :content="false" color="neutral" size="sm" :ui="{ ...SEGMENTED_UI, root: 'w-full sm:w-fit' }" />
      <DatasourcesPermissionList v-if="tab === 'operations'" :engine="engine" :access="access" />
      <DatasourcesGrantScript v-else :engine="engine" :settings="settings" :access="access" />
    </div>
  </div>
</template>
