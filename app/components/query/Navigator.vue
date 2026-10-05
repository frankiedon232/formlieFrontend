<!--
  The Query editor's panel in the menu column (F12 M4, the explorer's mode): the connection, then
  Tables (the explorer's tree; a click puts the table's name at the cursor) and History (this
  person's recent statements on the connection; a click opens one in a new tab). Right-click for
  more: SELECT the first rows, insert or copy a name, open / copy / remove a statement.
-->
<script setup lang="ts">
import type { DataSourceRow } from '#shared/types/datasources'
import type { DatabaseTable } from '#shared/types/destinations'
import type { ExplorerNode } from '#shared/types/explorer'
import type { QueryHistoryItem } from '#shared/types/query'
import type { DbEngine } from '#shared/utils/integrations/databases'

const props = defineProps<{ sources: DataSourceRow[] | null; sourceId: string | null; tables: DatabaseTable[] | null; loading?: boolean; history: QueryHistoryItem[] | null; engine: DbEngine | null }>()
const emit = defineEmits<{ source: [id: string]; insert: [text: string]; open: [sql: string, newTab: boolean]; select: [table: DatabaseTable]; remove: [id?: string] }>()
const { t } = useI18n()
const { relative, number } = useFormat()
const toast = useToast()
const { copy } = useClipboard({ legacy: true })
const tab = ref<'tables' | 'history'>('tables')
const tabs = computed(() => [
  { value: 'tables', label: t('query.side.tables'), icon: 'i-lucide-list-tree' },
  { value: 'history', label: t('query.side.history'), icon: 'i-lucide-history' },
])

const name = (schema: string, table: string) => `${schema}.${table}`
/** The first rows of a table, written the connection's way (LIMIT · TOP · FETCH FIRST). */
const firstRows = (table: string) =>
  props.engine === 'sqlserver'
    ? `SELECT TOP 100 *\nFROM ${table};`
    : props.engine === 'oracle'
      ? `SELECT *\nFROM ${table}\nFETCH FIRST 100 ROWS ONLY;`
      : `SELECT *\nFROM ${table}\nLIMIT 100;`
function copyText(text: string) {
  void copy(text)
  toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
}

const root = useTemplateRef<HTMLElement>('root')
useContextMenu().register(root, target => {
  const nodeLabel = target.closest('[role="treeitem"]')?.querySelector('[data-explorer-node]')
  if (nodeLabel) {
    const node = JSON.parse(nodeLabel.getAttribute('data-explorer-node')!) as ExplorerNode
    if (node.kind === 'schema') return [[{ label: t('explorer.ddl.copyName'), icon: 'i-lucide-copy', onSelect: () => copyText(node.schema) }]]
    const full = name(node.schema, node.table)
    if (node.kind === 'column') return [[{ label: t('query.side.insertName'), icon: 'i-lucide-text-cursor-input', onSelect: () => emit('insert', node.column) }, { label: t('explorer.ddl.copyName'), icon: 'i-lucide-copy', onSelect: () => copyText(node.column) }]]
    return [
      [{ label: t('query.side.selectRows'), icon: 'i-lucide-play', onSelect: () => emit('open', firstRows(full), true) }],
      [
        { label: t('query.side.insertName'), icon: 'i-lucide-text-cursor-input', onSelect: () => emit('insert', full) },
        { label: t('explorer.ddl.copyName'), icon: 'i-lucide-copy', onSelect: () => copyText(full) },
      ],
    ]
  }
  const id = target.closest('[data-history]')?.getAttribute('data-history')
  const item = id ? props.history?.find(entry => entry.id === id) : undefined
  if (item)
    return [
      [
        { label: t('query.side.openNewTab'), icon: 'i-lucide-square-plus', onSelect: () => emit('open', item.sql, true) },
        { label: t('query.side.openHere'), icon: 'i-lucide-square-pen', onSelect: () => emit('open', item.sql, false) },
        { label: t('query.side.insertAtCursor'), icon: 'i-lucide-text-cursor-input', onSelect: () => emit('insert', item.sql) },
      ],
      [{ label: t('contextMenu.copy'), icon: 'i-lucide-copy', onSelect: () => copyText(item.sql) }],
      [{ label: t('query.side.remove'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => emit('remove', item.id) }],
    ]
  return null
})
</script>

<template>
  <div ref="root" class="flex min-h-0 flex-1 flex-col gap-2 p-3">
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
    <UTabs v-model="tab" :items="tabs" :content="false" color="neutral" size="xs" :ui="{ ...SEGMENTED_UI, root: 'w-full', list: `${SEGMENTED_UI.list} w-full`, trigger: `${SEGMENTED_UI.trigger} flex-1` }" />

    <ExplorerTree v-if="tab === 'tables'" :tables="tables" :selected="null" :loading="loading" class="flex-1" @select="table => emit('select', table)" />

    <template v-else>
      <div v-if="!history" class="flex flex-col gap-2"><USkeleton v-for="n in 5" :key="n" class="h-12 rounded-md" /></div>
      <AppEmpty v-else-if="!history.length" size="xs" icon="i-lucide-history" :title="t('query.side.noHistory')" :description="t('query.side.noHistoryDesc')" />
      <template v-else>
        <ul class="-mx-1 flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto">
          <li v-for="item in history" :key="item.id">
            <button
              type="button"
              :data-history="item.id"
              class="flex w-full flex-col gap-1 rounded-md px-2 py-1.5 text-start hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :title="item.sql"
              @click="emit('open', item.sql, true)"
            >
              <code class="line-clamp-2 font-mono text-[11px] break-all text-highlighted" dir="ltr">{{ item.sql }}</code>
              <span class="flex items-center gap-1.5 text-[10px] text-muted">
                <span class="size-1.5 shrink-0 rounded-full" :class="item.ok ? 'bg-success' : 'bg-error'" aria-hidden="true" />
                <span>{{ t(`query.kind.${item.kind}`) }}</span>
                <span v-if="item.rows != null" class="tabular-nums">· {{ t('query.side.rows', { n: number(item.rows) }, item.rows) }}</span>
                <span class="ms-auto">{{ relative(item.ran_at) }}</span>
              </span>
            </button>
          </li>
        </ul>
        <UButton :label="t('query.side.clear')" icon="i-lucide-trash-2" color="neutral" variant="ghost" size="xs" class="self-start" @click="emit('remove')" />
      </template>
    </template>
  </div>
</template>
