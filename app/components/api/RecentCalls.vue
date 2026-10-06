<!--
  Recent calls on the API service overview (the design's "Recent Tasks" table): the latest calls to
  your endpoints with method, address, result, time taken, token and when; a row opens it in
  Request logs; "See all" opens the log.
-->
<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { ApiLogEntry } from '#shared/types/apiService'

const { t } = useI18n()
const api = useApi()
const { relative, dateTime } = useFormat()
const calls = ref<ApiLogEntry[] | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    calls.value = (await api.list<ApiLogEntry>('/api-logs', { page_size: 6 })).data
  } catch {
    failed.value = true
    calls.value = []
  }
}
onMounted(load)
const columns = computed<TableColumn<ApiLogEntry>[]>(() => [
  { accessorKey: 'path', header: t('apiService.logs.col.call') },
  { accessorKey: 'status', header: t('apiService.logs.col.status') },
  { accessorKey: 'duration_ms', header: t('apiService.logs.col.duration'), meta: { class: { th: 'hidden md:table-cell', td: 'hidden md:table-cell' } } },
  { id: 'token', header: t('apiService.logs.col.token'), meta: { class: { th: 'hidden sm:table-cell', td: 'hidden sm:table-cell' } } },
  { accessorKey: 'at', header: t('dataSources.home.col.when') },
])
const open = (_: Event, row: { original: ApiLogEntry }) => void navigateTo({ path: '/api-service/logs', query: { log: row.original.id } })
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
    <div class="flex items-center justify-between gap-2">
      <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.home.recent') }}</h2>
      <UButton :label="t('dataSources.home.seeAll')" trailing-icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" to="/api-service/logs" />
    </div>
    <div v-if="!calls" class="flex flex-col gap-2"><USkeleton v-for="n in 5" :key="n" class="h-9 w-full" /></div>
    <AppEmpty v-else-if="!calls.length" size="xs" :icon="failed ? 'i-lucide-cloud-alert' : 'i-lucide-scroll-text'" :title="failed ? t('dataView.errorTitle') : t('apiService.logs.empty')" :actions="failed ? [{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: load }] : undefined" />
    <UTable v-else :data="calls" :columns="columns" class="-mx-1" :ui="{ thead: 'bg-elevated/50', th: 'py-2 text-xs font-medium text-muted', td: 'py-2.5 text-sm', tr: 'cursor-pointer hover:bg-elevated/50' }" @select="open">
      <template #path-cell="{ row }">
        <span class="flex min-w-0 items-center gap-2">
          <UBadge :label="row.original.method" color="neutral" variant="outline" size="xs" class="w-14 shrink-0 justify-center rounded-md font-mono" />
          <span class="block max-w-64 truncate font-mono text-xs text-highlighted" dir="ltr">{{ row.original.endpoint ? `/${row.original.endpoint.name}` : row.original.path }}</span>
        </span>
      </template>
      <template #status-cell="{ row }"><ApiLogsStatus :status="row.original.status" :code="row.original.code" /></template>
      <template #duration_ms-cell="{ row }"><span class="text-muted tabular-nums">{{ t('dataSources.ms', { n: row.original.duration_ms }) }}</span></template>
      <template #token-cell="{ row }"><span class="block max-w-40 truncate">{{ row.original.token?.name ?? t('apiService.logs.noToken') }}</span></template>
      <template #at-cell="{ row }">
        <UTooltip :text="dateTime(row.original.at)"><span class="whitespace-nowrap text-muted">{{ relative(row.original.at) }}</span></UTooltip>
      </template>
    </UTable>
  </UCard>
</template>
