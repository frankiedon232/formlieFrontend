<!-- Step 1 of a new connection: which database (arrow keys move between them, like any radio group). -->
<script setup lang="ts">
import type { DbEngine } from '#shared/types/datasources'
import { SUPPORTED_DATABASES } from '#shared/utils/integrations/databases'

const engine = defineModel<DbEngine | null>({ required: true })
const { t } = useI18n()
const items = computed(() => SUPPORTED_DATABASES.map(db => ({ value: db.key, label: db.name, description: t(`dataSources.engineDesc.${db.key}`) })))
</script>

<template>
  <div class="flex flex-col gap-4">
    <URadioGroup
      :model-value="engine ?? undefined"
      :items="items"
      variant="card"
      indicator="end"
      color="neutral"
      :legend="t('dataSources.wizard.engineLegend')"
      :ui="{ fieldset: 'grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3', legend: 'sr-only', item: 'items-start has-data-[state=checked]:border-inverted', wrapper: 'min-w-0' }"
      @update:model-value="value => (engine = value as DbEngine)"
    >
      <template #label="{ item }">
        <span class="flex items-center gap-2.5">
          <DatasourcesEngineLogo :engine="String(item.value)" size="sm" />
          <span class="font-semibold text-highlighted">{{ item.label }}</span>
        </span>
      </template>
      <template #description="{ item }">
        <span class="mt-1.5 block text-xs text-muted">{{ item.description }}</span>
      </template>
    </URadioGroup>
    <p class="flex items-center gap-1.5 text-xs text-muted">
      <UIcon name="i-lucide-shield-check" class="size-3.5 shrink-0" />
      {{ t('dataSources.wizard.builtInNote') }}
    </p>
  </div>
</template>
