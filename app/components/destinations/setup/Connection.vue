<!-- Step 1: which connection keeps this form's responses (arrow keys move between them). -->
<script setup lang="ts">
const props = defineProps<{ setup: ReturnType<typeof useStorageSetup> }>()
const { t } = useI18n()
const { can } = useCan()
onMounted(() => !props.setup.sources.value && void props.setup.loadSources())
const { sourceId } = props.setup
const choose = (value: unknown) => (sourceId.value = String(value))
const items = computed(() =>
  (props.setup.sources.value ?? []).map(source => ({
    value: source.id,
    label: source.name,
    description: `${engineName(source.engine)} · ${source.address}`,
    source,
  })),
)
</script>

<template>
  <div class="flex flex-col gap-4">
    <div v-if="!setup.sources.value" class="grid grid-cols-1 gap-3 sm:grid-cols-2"><USkeleton v-for="n in 4" :key="n" class="h-20 rounded-lg" /></div>
    <AppEmpty
      v-else-if="!items.length"
      icon="i-lucide-database"
      :title="t('destinations.setup.noConnections')"
      :description="t('destinations.setup.noConnectionsDesc')"
      :actions="can('data.create') ? [{ label: t('dataSources.add'), icon: 'i-lucide-plus', color: 'neutral', to: '/data-sources/connections/new' }] : []"
      variant="outline"
    />
    <URadioGroup
      v-else
      :model-value="setup.sourceId.value ?? undefined"
      :items="items"
      variant="card"
      indicator="end"
      color="neutral"
      :legend="t('destinations.setup.step.connection')"
      :ui="{ fieldset: 'grid grid-cols-1 gap-3 sm:grid-cols-2', legend: 'sr-only', item: 'items-start has-data-[state=checked]:border-inverted', wrapper: 'min-w-0' }"
      @update:model-value="choose"
    >
      <template #label="{ item }">
        <span class="flex min-w-0 items-center gap-2.5">
          <DatasourcesEngineLogo :engine="item.source.engine" size="sm" />
          <span class="truncate font-semibold text-highlighted">{{ item.label }}</span>
          <DataStatusBadge :status="item.source.status" class="ms-auto" />
        </span>
      </template>
      <template #description="{ item }">
        <span class="mt-1.5 flex flex-col gap-1 text-xs text-muted">
          <span class="truncate text-start font-mono" dir="ltr">{{ item.description }}</span>
          <span>{{ t('dataSources.summary.access') }}: {{ t(`dataSources.access.other.${item.source.access.other}`) }} · {{ t('dataSources.access.prefix') }}: <code class="font-mono">{{ item.source.access.table_prefix }}</code></span>
        </span>
      </template>
    </URadioGroup>
    <UAlert v-if="setup.source.value && (setup.source.value.status === 'failing' || setup.source.value.status === 'untested')" icon="i-lucide-triangle-alert" color="warning" variant="subtle" :title="t('destinations.setup.connectionWarn')" :description="t('destinations.setup.connectionWarnDesc')" />
  </div>
</template>
