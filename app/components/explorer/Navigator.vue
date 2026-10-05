<!--
  The explorer's way around (F12 M3): the connection picker, then its schemas, tables and
  columns (ExplorerTree). Lives in the sidebar's menu column on desktop (useSidebarTakeover) and
  in a panel from the side on phones, tablets and with the sidebar folded.
-->
<script setup lang="ts">
import type { DataSourceRow } from '#shared/types/datasources'
import type { DatabaseTable } from '#shared/types/destinations'

defineProps<{ sources: DataSourceRow[] | null; sourceId: string | null; tables: DatabaseTable[] | null; selected: string | null; loading?: boolean }>()
const emit = defineEmits<{ source: [id: string]; select: [table: DatabaseTable] }>()
const { t } = useI18n()
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-3 p-3">
    <USkeleton v-if="!sources" class="h-8 rounded-md" />
    <USelectMenu
      v-else-if="sources.length"
      :model-value="sourceId ?? undefined"
      :items="sources.map(item => ({ value: item.id, label: item.name, icon: engineIcon(item.engine) }))"
      value-key="value"
      :icon="engineIcon(sources.find(item => item.id === sourceId)?.engine ?? '')"
      class="w-full"
      :aria-label="t('explorer.connection')"
      @update:model-value="value => emit('source', String(value))"
    />
    <ExplorerTree v-if="sources?.length !== 0" :tables="tables" :selected="selected" :loading="loading" class="flex-1" @select="table => emit('select', table)" />
  </div>
</template>
