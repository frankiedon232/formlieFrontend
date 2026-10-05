<!--
  Export the table, or the rows matching the current search and filters, as CSV, Excel, JSON or SQL
  INSERT statements for the connection's engine (F12 M3).
  The file is made on Formalie's servers with a percentage shown on the button, then downloaded
  through a one-time private link. Recorded in the audit trail.
-->
<script setup lang="ts">
import type { TableExport } from '#shared/types/explorer'

const props = defineProps<{ sourceId: string; schema: string; table: string; params: () => Record<string, string | number>; filtered: boolean }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const job = ref<TableExport | null>(null)
const running = computed(() => !!job.value && job.value.status === 'running')

async function start(format: TableExport['format']) {
  const { q, sort, ...rest } = props.params()
  const filter = Object.fromEntries(Object.entries(rest).filter(([key]) => key.startsWith('filter[')).map(([key, value]) => [key.slice(7, -1), String(value)]))
  try {
    job.value = (await api.post<TableExport>(`/datasources/${props.sourceId}/explorer/exports`, { schema: props.schema, table: props.table, format, q: q ? String(q) : undefined, sort: sort ? String(sort) : undefined, filter })).data
    while (job.value.status === 'running') {
      await new Promise(resolve => setTimeout(resolve, 400))
      job.value = (await api.get<TableExport>(`/explorer-exports/${job.value.id}`, undefined, { background: true })).data
    }
    const { data } = await api.post<{ url: string }>(`/explorer-exports/${job.value.id}/link`)
    const link = document.createElement('a')
    link.href = data.url
    link.rel = 'noopener'
    link.click()
    toast.add({ title: t('explorer.exported', { n: job.value.rows }, job.value.rows), color: 'success', icon: 'i-lucide-file-down' })
  } catch (error) {
    handle(error)
  } finally {
    job.value = null
  }
}
const items = computed(() => [
  [{ type: 'label' as const, label: props.filtered ? t('explorer.exportFiltered') : t('explorer.exportAll') }],
  [
    { label: t('responses.export.format.xlsx'), icon: 'i-lucide-file-spreadsheet', onSelect: () => void start('xlsx') },
    { label: t('responses.export.format.csv'), icon: 'i-lucide-file-text', onSelect: () => void start('csv') },
  ],
  [
    { label: t('explorer.exportJson'), description: t('explorer.exportJsonDesc'), icon: 'i-lucide-file-json', onSelect: () => void start('json') },
    { label: t('explorer.exportSql'), description: t('explorer.exportSqlDesc'), icon: 'i-lucide-file-code', onSelect: () => void start('sql') },
  ],
])
</script>

<template>
  <UDropdownMenu :items="items" :content="{ align: 'end' }" :disabled="running">
    <UButton :label="running ? t('explorer.exporting', { n: job?.progress ?? 0 }) : t('explorer.export')" icon="i-lucide-file-down" color="neutral" variant="outline" :loading="running" class="tabular-nums" />
  </UDropdownMenu>
</template>
