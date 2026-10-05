<!--
  What a run produced (F12 M4): the results grid for reading statements; for changes, how many rows
  and how long; the database's problem with the line it points at; a calm start state with the
  shortcut; a slim progress bar while it runs (old results stay, dimmed).
-->
<script setup lang="ts">
import type { TableExport } from '#shared/types/explorer'
const props = defineProps<{ state: RunState; sourceId: string | null }>()
const emit = defineEmits<{ page: [page: number]; line: [line: number] }>()
const { t } = useI18n()
const { number } = useFormat()
const api = useApi()
// Export: the same statement again on the server, this page or up to 5,000 rows (never from the browser's copy)
const exportResults = async (format: TableExport['format'], scope: TableExport['scope']) =>
  (await api.post<TableExport>(`/datasources/${props.sourceId}/query/export`, { sql: props.state.last!.text, params: props.state.last!.params, format, scope, page: props.state.result!.page, page_size: props.state.result!.page_size })).data
</script>

<template>
  <div class="relative flex min-h-0 flex-1 flex-col" :aria-busy="state.running">
    <UProgress v-if="state.running" animation="swing" color="neutral" size="2xs" class="absolute inset-x-0 top-0 z-20" />
    <AppEmpty
      v-if="state.problem"
      size="sm"
      :icon="state.problem.line ? 'i-lucide-circle-x' : 'i-lucide-octagon-alert'"
      :title="state.problem.title"
      :description="state.problem.description"
      :actions="state.problem.line ? [{ label: t('query.goToLine', { n: state.problem.line }), icon: 'i-lucide-corner-down-right', color: 'neutral', variant: 'outline', onClick: () => emit('line', state.problem!.line!) }] : undefined"
    />
    <template v-else-if="state.result">
      <div class="flex min-h-0 flex-1 flex-col transition-opacity" :class="state.running ? 'opacity-60' : ''">
        <QueryResults v-if="state.result.kind === 'read'" :result="state.result" @page="page => emit('page', page)">
          <template #actions>
            <ExplorerExportButton v-if="sourceId && state.last && state.result.rows.length" :source-id="sourceId" :page-rows="state.result.rows.length" :create="exportResults" :formats="['xlsx', 'csv', 'json']" size="xs" />
          </template>
        </QueryResults>
        <AppEmpty
          v-else
          size="sm"
          :icon="state.result.notice ? 'i-lucide-info' : 'i-lucide-circle-check'"
          :title="state.result.notice ? t('query.structurePreview') : t(`query.done.${state.result.kind}`, { n: number(state.result.rows_affected ?? 0) }, state.result.rows_affected ?? 0)"
          :description="t('query.took', { ms: number(state.result.duration_ms) })"
        />
      </div>
    </template>
    <AppEmpty v-else-if="!state.running" size="sm" icon="i-lucide-square-terminal" :title="t('query.startTitle')" :description="t('query.startDesc')" />
  </div>
</template>
