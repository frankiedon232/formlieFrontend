<!--
  Step 2: a new table made from the form (named with the connection's prefix, in its schema for
  response tables), or a table of theirs (needs Full access on the connection).
-->
<script setup lang="ts">
const props = defineProps<{ setup: ReturnType<typeof useStorageSetup>; nameError?: string }>()
const { t } = useI18n()
const { number } = useFormat()
const s = props.setup

const modes = computed(() => [
  { value: 'create', label: t('destinations.setup.create'), description: t('destinations.setup.createDesc') },
  { value: 'existing', label: t('destinations.setup.existing'), description: s.fullAccess.value ? t('destinations.setup.existingDesc') : t('destinations.setup.existingNeedsFull'), disabled: !s.fullAccess.value },
])
const tableItems = computed(() =>
  s.theirTables.value.map(table => ({ value: `${table.schema}.${table.name}`, label: `${table.schema}.${table.name}`, description: t('destinations.setup.tableFacts', { columns: table.columns.length, rows: table.rows_estimate === null ? '–' : number(table.rows_estimate) }) })),
)
</script>

<template>
  <div class="flex flex-col gap-5">
    <div v-if="s.loadingTables.value && !s.tables.value" class="flex flex-col gap-3"><USkeleton class="h-20 rounded-lg" /><USkeleton class="h-20 rounded-lg" /></div>
    <template v-else>
      <URadioGroup
        :model-value="s.mode.value"
        :items="modes"
        variant="card"
        indicator="end"
        color="neutral"
        :legend="t('destinations.setup.step.table')"
        :ui="{ fieldset: 'grid grid-cols-1 gap-3 sm:grid-cols-2', legend: 'sr-only', item: 'items-start has-data-[state=checked]:border-inverted' }"
        @update:model-value="value => (s.mode.value = value as 'create' | 'existing')"
      >
        <template #label="{ item }">
          <span class="flex flex-wrap items-center gap-2">
            <span class="font-medium text-highlighted">{{ item.label }}</span>
            <UBadge v-if="item.value === 'create'" :label="t('destinations.setup.recommended')" color="neutral" size="sm" class="rounded-md" />
          </span>
        </template>
      </URadioGroup>

      <div v-if="s.mode.value === 'create'" class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <UFormField :label="t('destinations.setup.tableName')" :description="t('destinations.setup.tableNameDesc', { prefix: s.prefix.value })" name="table" :error="nameError ?? (s.nameTaken.value ? t('errors.FRM-DEST-1014') : undefined)" required>
          <UInput v-model="s.tableName.value" maxlength="63" class="w-full font-mono" dir="ltr" spellcheck="false">
            <template #trailing>
              <UButton icon="i-lucide-rotate-ccw" color="neutral" variant="link" size="xs" :aria-label="t('destinations.setup.suggest')" @click="s.tableName.value = s.suggestedName()" />
            </template>
          </UInput>
        </UFormField>
        <div class="flex flex-col gap-1 text-sm">
          <span class="font-medium text-highlighted">{{ t('dataSources.access.tablesSchema') }}</span>
          <span class="text-xs text-muted">{{ t('destinations.setup.schemaFromConnection') }}</span>
          <code class="w-fit rounded bg-elevated px-1.5 py-0.5 font-mono text-xs" dir="ltr">{{ s.tablesSchema.value || '…' }}</code>
        </div>
      </div>

      <UFormField v-else :label="t('destinations.setup.pickTable')" :description="t('destinations.setup.pickTableDesc')" name="table" :error="nameError" required>
        <USelectMenu
          :model-value="s.existingKey.value ?? undefined"
          :items="tableItems"
          value-key="value"
          :search-input="{ placeholder: t('destinations.setup.searchTables') }"
          :placeholder="t('destinations.setup.pickTable')"
          class="w-full font-mono"
          @update:model-value="value => (s.existingKey.value = String(value))"
        />
      </UFormField>
    </template>
  </div>
</template>
