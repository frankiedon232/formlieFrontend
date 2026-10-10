<!--
  The explorer's way around (F12 M3): the connection picker, then its schemas, tables and
  columns (ExplorerTree). Lives in the sidebar's menu column on desktop (useSidebarTakeover) and
  in a panel from the side on phones, tablets and with the sidebar folded. Right-click on a node
  opens its menu (`menu`).
-->
<script setup lang="ts">
import type { DataSourceRow } from '#shared/types/datasources'
import type { DatabaseTable, TableColumn } from '#shared/types/destinations'
import type { ExplorerNode } from '#shared/types/explorer'

const props = defineProps<{ sources: DataSourceRow[] | null; sourceId: string | null; tables: DatabaseTable[] | null; columns: Map<string, TableColumn[]>; truncated?: boolean; total?: number; selected: string | null; loading?: boolean; menu?: (node: ExplorerNode) => ContextMenuGroups }>()
const emit = defineEmits<{ source: [id: string]; select: [table: DatabaseTable]; expand: [table: DatabaseTable]; search: [q: string] }>()
const { t } = useI18n()

// Right-click on a schema, table or column: its own menu (the page decides what it offers)
const root = useTemplateRef<HTMLElement>('root')
useContextMenu().register(root, target => {
  const label = target.closest('[role="treeitem"]')?.querySelector('[data-explorer-node]')
  return label && props.menu ? props.menu(JSON.parse(label.getAttribute('data-explorer-node')!) as ExplorerNode) : null
})
</script>

<template>
  <div ref="root" class="flex min-h-0 min-w-0 flex-1 flex-col gap-2 p-3">
    <USkeleton v-if="!sources" class="h-7 rounded-sm" />
    <USelectMenu
      v-else-if="sources.length"
      :model-value="sourceId ?? undefined"
      :items="sources.map(item => ({ value: item.id, label: item.name, icon: engineIcon(item.engine) }))"
      value-key="value"
      size="xs"
      :ui="{ base: 'h-7 rounded-sm' }"
      :icon="engineIcon(sources.find(item => item.id === sourceId)?.engine ?? '')"
      class="w-full"
      :aria-label="t('explorer.connection')"
      @update:model-value="value => emit('source', String(value))"
    />
    <ExplorerTree v-if="sources?.length !== 0" :tables="tables" :columns="columns" :truncated="truncated" :total="total" :selected="selected" :loading="loading" class="flex-1" @select="table => emit('select', table)" @expand="table => emit('expand', table)" @search="q => emit('search', q)" />
  </div>
</template>
