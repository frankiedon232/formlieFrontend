<!--
  What a run produced (F12 M4): the results grid for reading statements; for changes, how many rows
  and how long; the database's problem with the line it points at; a calm start state with the
  shortcut; a slim progress bar while it runs (old results stay, dimmed). Run all: a sliding row
  of the statements (status icon, number, its start) above the chosen one's result.
-->
<script setup lang="ts">
import type { TableExport } from '#shared/types/explorer'
import { EXPORT_MAX_ROWS } from '#shared/utils/datasources/exportFormats'
const props = defineProps<{ state: RunState; sourceId: string | null }>()
const emit = defineEmits<{ page: [page: number]; line: [line: number]; show: [index: number] }>()
const { t } = useI18n()
const { number } = useFormat()
const { can } = useCan()
const api = useApi()

// The shown outcome: the chosen statement of Run all, or the single run
const shown = computed(() => {
  const item = props.state.batch?.[props.state.active]
  if (item) return { result: item.result, problem: item.problem, text: item.text, params: item.params, status: item.status }
  return { result: props.state.result, problem: props.state.problem, text: props.state.last?.text ?? '', params: props.state.last?.params ?? {}, status: null }
})
const STATUS_ICON = { waiting: 'i-lucide-circle-dashed', running: 'i-lucide-loader-circle', done: 'i-lucide-circle-check', failed: 'i-lucide-circle-x', skipped: 'i-lucide-circle-minus' } as const
const snippet = (text: string) => text.replace(/--[^\n]*|\/\*[\s\S]*?\*\//g, ' ').replace(/\s+/g, ' ').trim().slice(0, 48)

// Export the result (owner 2026-10-05): the same statement again on the server, all its rows up to 5,000 (never the browser's copy)
const exportResults = async (format: TableExport['format'], scope: TableExport['scope']) =>
  (await api.post<TableExport>(`/datasources/${props.sourceId}/query/export`, { sql: shown.value.text, params: shown.value.params, format, scope, page: shown.value.result!.page, page_size: shown.value.result!.page_size })).data
</script>

<template>
  <div class="relative flex min-h-0 flex-1 flex-col" :aria-busy="state.running">
    <UProgress v-if="state.running" animation="swing" color="neutral" size="2xs" class="absolute inset-x-0 top-0 z-20" />

    <!-- Run all: one tab per statement -->
    <div v-if="state.batch" role="tablist" :aria-label="t('query.runAll.results')" class="flex shrink-0 items-center gap-1 overflow-x-auto border-b border-default bg-elevated/30 px-2 py-1">
      <UButton
        v-for="(item, index) in state.batch"
        :key="index"
        role="tab"
        :aria-selected="index === state.active"
        size="xs"
        color="neutral"
        :variant="index === state.active ? 'outline' : 'ghost'"
        :disabled="item.status === 'waiting' || (item.status === 'skipped' && !item.result)"
        :title="item.text"
        class="max-w-64 shrink-0"
        @click="emit('show', index)"
      >
        <UIcon :name="STATUS_ICON[item.status]" class="size-3.5 shrink-0" :class="[item.status === 'running' ? 'animate-spin' : '', item.status === 'failed' ? 'text-error' : item.status === 'done' ? 'text-success' : 'text-muted']" />
        <span class="font-medium tabular-nums">{{ index + 1 }}</span>
        <span class="truncate font-mono text-muted">{{ snippet(item.text) }}</span>
      </UButton>
      <span class="ms-auto shrink-0 ps-2 text-xs text-muted">{{ t('query.runAll.summary', { done: state.batch.filter(item => item.status === 'done').length, n: state.batch.length }) }}</span>
    </div>

    <AppEmpty
      v-if="shown.problem"
      size="sm"
      :icon="shown.problem.line ? 'i-lucide-circle-x' : 'i-lucide-octagon-alert'"
      :title="shown.problem.title"
      :description="shown.problem.description"
      :actions="shown.problem.line ? [{ label: t('query.goToLine', { n: shown.problem.line }), icon: 'i-lucide-corner-down-right', color: 'neutral', variant: 'outline', onClick: () => emit('line', shown.problem!.line!) }] : undefined"
    />
    <template v-else-if="shown.result">
      <div class="flex min-h-0 flex-1 flex-col transition-opacity" :class="state.running && !state.batch ? 'opacity-60' : ''">
        <QueryResults v-if="shown.result.kind === 'read'" :result="shown.result" @page="page => emit('page', page)">
          <template #actions>
            <ExplorerExportButton v-if="sourceId && can('data.export') && shown.text && shown.result.rows.length" :source-id="sourceId" :page-rows="shown.result.rows.length" :create="exportResults" :formats="['xlsx', 'csv', 'json']" :result-label="t('query.exportResult', { n: number(Math.min(shown.result.total ?? 0, EXPORT_MAX_ROWS)) }, Math.min(shown.result.total ?? 0, EXPORT_MAX_ROWS))" size="xs" />
          </template>
        </QueryResults>
        <AppEmpty
          v-else
          size="sm"
          :icon="shown.result.notice ? 'i-lucide-info' : 'i-lucide-circle-check'"
          :title="shown.result.notice ? t('query.structurePreview') : t(`query.done.${shown.result.kind}`, { n: number(shown.result.rows_affected ?? 0) }, shown.result.rows_affected ?? 0)"
          :description="t('query.took', { ms: number(shown.result.duration_ms) })"
        />
      </div>
    </template>
    <AppEmpty v-else-if="shown.status === 'skipped'" size="sm" icon="i-lucide-circle-minus" :title="t('query.runAll.skipped')" :description="t('query.runAll.skippedDesc')" />
    <AppEmpty v-else-if="!state.running" size="sm" icon="i-lucide-square-terminal" :title="t('query.startTitle')" :description="t('query.startDesc')" />
  </div>
</template>
