<!--
  Export rows as CSV, Excel, JSON or SQL INSERT statements for the connection's engine (F12 M3).
  This page (the rows on screen, with the search, filters and sort) first; "All rows" is a
  deliberate choice and stops at EXPORT_MAX_ROWS (owner 2026-10-05), saying so when it does.
  The file is made on Formalie's servers with a percentage shown on the button, then downloaded
  through a one-time private link. Recorded in the audit trail.
-->
<script setup lang="ts">
import type { TableExport } from '#shared/types/explorer'
import { EXPORT_MAX_ROWS } from '#shared/utils/datasources/exportFormats'

const props = withDefaults(
  defineProps<{
    sourceId: string
    schema?: string
    table?: string
    params?: () => Record<string, string | number>
    filtered?: boolean
    pageRows: number
    /** Make the file another way (the Query editor exports a statement's results). */
    create?: (format: TableExport['format'], scope: TableExport['scope']) => Promise<TableExport>
    formats?: TableExport['format'][]
    size?: 'xs' | 'sm' | 'md'
  }>(),
  { schema: '', table: '', params: () => ({}), filtered: false, create: undefined, formats: () => ['xlsx', 'csv', 'json', 'sql'], size: 'md' },
)
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { number } = useFormat()
const job = ref<TableExport | null>(null)
const running = computed(() => !!job.value && job.value.status === 'running')

async function start(format: TableExport['format'], scope: TableExport['scope'] = 'page') {
  const { q, sort, page, page_size: pageSize, ...rest } = props.params()
  const filter = Object.fromEntries(Object.entries(rest).filter(([key]) => key.startsWith('filter[')).map(([key, value]) => [key.slice(7, -1), String(value)]))
  try {
    job.value = props.create
      ? await props.create(format, scope)
      : (await api.post<TableExport>(`/datasources/${props.sourceId}/explorer/exports`, { schema: props.schema, table: props.table, format, scope, page, page_size: pageSize, q: q ? String(q) : undefined, sort: sort ? String(sort) : undefined, filter })).data
    while (job.value.status === 'running') {
      await new Promise(resolve => setTimeout(resolve, 400))
      job.value = (await api.get<TableExport>(`/explorer-exports/${job.value.id}`, undefined, { background: true })).data
    }
    const { data } = await api.post<{ url: string }>(`/explorer-exports/${job.value.id}/link`)
    const link = document.createElement('a')
    link.href = data.url
    link.rel = 'noopener'
    link.click()
    toast.add(
      job.value.capped
        ? { title: t('explorer.exported', { n: number(job.value.rows) }, job.value.rows), description: t('explorer.exportCapped', { total: number(job.value.total), max: number(EXPORT_MAX_ROWS) }), color: 'warning', icon: 'i-lucide-file-down' }
        : { title: t('explorer.exported', { n: number(job.value.rows) }, job.value.rows), color: 'success', icon: 'i-lucide-file-down' },
    )
  } catch (error) {
    handle(error)
  } finally {
    job.value = null
  }
}
defineExpose({ start, running })
const FORMATS = { xlsx: ['responses.export.format.xlsx', 'i-lucide-file-spreadsheet'], csv: ['responses.export.format.csv', 'i-lucide-file-text'], json: ['explorer.exportJson', 'i-lucide-file-json'], sql: ['explorer.exportSql', 'i-lucide-file-code'] } as const
const formats = (scope: TableExport['scope']) => props.formats.map(format => ({ label: t(FORMATS[format][0]), icon: FORMATS[format][1], onSelect: () => void start(format, scope) }))
const items = computed(() => [
  [{ type: 'label' as const, label: t('explorer.exportPage', { n: number(props.pageRows) }, props.pageRows) }, ...formats('page')],
  [{ type: 'label' as const, label: props.filtered ? t('explorer.exportMatching', { max: number(EXPORT_MAX_ROWS) }) : t('explorer.exportAllRows', { max: number(EXPORT_MAX_ROWS) }) }, ...formats('all')],
])
</script>

<template>
  <UDropdownMenu :items="items" :content="{ align: 'end' }" :disabled="running">
    <UButton :label="running ? t('explorer.exporting', { n: job?.progress ?? 0 }) : t('explorer.export')" icon="i-lucide-file-down" color="neutral" variant="outline" :size="size" :loading="running" class="tabular-nums" />
  </UDropdownMenu>
</template>
