<!--
  Access step (owner 2026-10-05): a connection exists to store the workspace's responses, so
  Formalie's own tables are always part of it: a table per form named with the chosen prefix,
  responses written there and read back to show them, rows changed and removed, columns added, in
  its own tables only (PostgreSQL / SQL Server: in the schema chosen here). The organisation's
  other tables are optional (not shared · read · read and write, default read and write) for the
  explorer, queries, option lists and imports. Below: every operation with its privilege, and the
  statements to run, written for this connection.
-->
<script setup lang="ts">
import { TABLE_PREFIXES, type DataSourceAccessSettings, type DataSourceSettings, type DbEngine, type OtherTablesAccess } from '#shared/types/datasources'
import { defaultSchemaOf } from '#shared/utils/datasources/engines'
import { hasTablesSchema, tablesSchemaOf } from '#shared/utils/datasources/permissions'

const props = defineProps<{ engine: DbEngine; settings: DataSourceSettings }>()
const access = defineModel<DataSourceAccessSettings>({ required: true })
const { t } = useI18n()

const set = (patch: Partial<DataSourceAccessSettings>) => (access.value = { ...access.value, ...patch })
const prefixes = TABLE_PREFIXES.map(value => ({ value, label: `${value}…` }))
const others = computed(() =>
  (['read_write', 'read', 'none'] as OtherTablesAccess[]).map(value => ({ value, label: t(`dataSources.access.other.${value}`), description: t(`dataSources.access.otherDesc.${value}`) })),
)
const isMysql = computed(() => props.engine === 'mysql' || props.engine === 'mariadb')
const tablesSchema = computed(() => tablesSchemaOf(props.engine, props.settings, { ...access.value, tables_schema: '' }))
const example = computed(() => `${access.value.table_prefix}job_application`)
const schemaHint = computed(() => (props.engine === 'oracle' ? t('dataSources.access.schemasHintOracle') : t(isMysql.value ? 'dataSources.access.databasesHint' : 'dataSources.access.schemasHint', { schema: defaultSchemaOf(props.engine, props.settings) || '…' })))
const tab = ref('operations')
const tabs = computed(() => [
  { value: 'operations', label: t('dataSources.access.tabOperations'), icon: 'i-lucide-list-checks' },
  { value: 'script', label: t('dataSources.access.tabScript'), icon: 'i-lucide-square-terminal' },
])
</script>

<template>
  <div class="flex flex-col gap-5">
    <!-- Your responses: Formalie's own tables, always -->
    <section class="flex flex-col gap-4 rounded-lg border border-inverted/40 p-3 sm:p-4">
      <div class="flex items-start justify-between gap-3">
        <div class="flex min-w-0 items-start gap-2.5">
          <UIcon name="i-lucide-inbox" class="mt-0.5 size-4 shrink-0 text-highlighted" />
          <div class="flex min-w-0 flex-col gap-0.5">
            <h3 class="text-sm font-semibold text-highlighted">{{ t('dataSources.access.ownTitle') }}</h3>
            <p class="text-xs text-muted">{{ t('dataSources.access.ownDesc') }}</p>
          </div>
        </div>
        <UBadge :label="t('dataSources.access.always')" color="neutral" size="sm" class="shrink-0 rounded-md" />
      </div>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <UFormField :label="t('dataSources.access.prefix')" :description="t('dataSources.access.prefixDesc', { example })">
          <USelect :model-value="access.table_prefix" :items="prefixes" value-key="value" class="w-full font-mono" @update:model-value="value => set({ table_prefix: value as DataSourceAccessSettings['table_prefix'] })" />
        </UFormField>
        <UFormField v-if="hasTablesSchema(engine)" :label="t('dataSources.access.tablesSchema')" :description="t(`dataSources.access.tablesSchemaDesc.${engine}`)">
          <UInput :model-value="access.tables_schema" :placeholder="tablesSchema" maxlength="128" class="w-full font-mono" dir="ltr" @update:model-value="value => set({ tables_schema: String(value).trim() })" />
        </UFormField>
        <div v-else class="flex flex-col gap-1 text-sm">
          <span class="font-medium text-highlighted">{{ isMysql ? t('dataSources.access.tablesDatabase') : t('dataSources.access.tablesSchema') }}</span>
          <span class="text-xs text-muted">{{ t(`dataSources.access.tablesSchemaDesc.${engine}`) }}</span>
          <code class="w-fit rounded bg-elevated px-1.5 py-0.5 font-mono text-xs" dir="ltr">{{ tablesSchema || '…' }}</code>
        </div>
      </div>
    </section>

    <!-- The organisation's other tables: optional, never used for responses -->
    <section class="flex flex-col gap-4 rounded-lg border border-default p-3 sm:p-4">
      <div class="flex items-start justify-between gap-3">
        <div class="flex min-w-0 items-start gap-2.5">
          <UIcon name="i-lucide-database" class="mt-0.5 size-4 shrink-0 text-muted" />
          <div class="flex min-w-0 flex-col gap-0.5">
            <h3 class="text-sm font-semibold text-highlighted">{{ t('dataSources.access.otherLegend') }}</h3>
            <p class="text-xs text-muted">{{ t('dataSources.access.otherHint') }}</p>
          </div>
        </div>
        <UBadge :label="t('dataSources.access.optional')" color="neutral" variant="outline" size="sm" class="shrink-0 rounded-md" />
      </div>
      <URadioGroup
        :model-value="access.other"
        :items="others"
        variant="card"
        indicator="end"
        color="neutral"
        :legend="t('dataSources.access.otherLegend')"
        :ui="{ fieldset: 'grid grid-cols-1 gap-3 sm:grid-cols-3', legend: 'sr-only', item: 'items-start has-data-[state=checked]:border-inverted' }"
        @update:model-value="value => set({ other: value as OtherTablesAccess })"
      />
      <UFormField v-if="access.other !== 'none'" :label="isMysql ? t('dataSources.access.databases') : t('dataSources.access.schemas')" :description="schemaHint">
        <UInputTags :model-value="access.schemas" :max-length="128" class="w-full font-mono" dir="ltr" @update:model-value="value => set({ schemas: (value as string[]).map(item => item.trim()).filter(Boolean).slice(0, 20) })" />
      </UFormField>
    </section>

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
