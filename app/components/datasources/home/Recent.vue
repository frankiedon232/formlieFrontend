<!--
  Recent activity on the Data sources overview (the design's "Recent Tasks" table): the latest
  events on the connections from the audit trail, kind dot, what happened, where, who and when;
  a row opens the event in Activity; "See all" opens Activity.
-->
<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { AuditEvent } from '#shared/types/audit'
import { ACTIVITY_COLOR, kindOfAction } from '#shared/utils/datasources/activity'

const { t } = useI18n()
const api = useApi()
const { relative, dateTime } = useFormat()
const format = useAuditFormat()

const events = ref<AuditEvent[] | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    events.value = (await api.list<AuditEvent>('/audit-logs', { 'filter[area]': 'data', page_size: 6, sort: '-occurred_at' })).data
  } catch {
    failed.value = true
    events.value = []
  }
}
onMounted(load)

const columns = computed<TableColumn<AuditEvent>[]>(() => [
  { accessorKey: 'action', header: t('dataSources.home.col.event') },
  { id: 'where', header: t('dataSources.home.col.where'), meta: { class: { th: 'hidden md:table-cell', td: 'hidden md:table-cell' } } },
  { id: 'who', header: t('dataSources.home.col.who'), meta: { class: { th: 'hidden sm:table-cell', td: 'hidden sm:table-cell' } } },
  { accessorKey: 'occurred_at', header: t('dataSources.home.col.when') },
])
const openEvent = (_: Event, row: { original: AuditEvent }) => void navigateTo({ path: '/data-sources/activity', query: { event: row.original.id } })
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
    <div class="flex items-center justify-between gap-2">
      <h2 class="text-sm font-semibold text-highlighted">{{ t('dataSources.home.recent') }}</h2>
      <UButton :label="t('dataSources.home.seeAll')" trailing-icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" to="/data-sources/activity" />
    </div>
    <div v-if="!events" class="flex flex-col gap-2"><USkeleton v-for="n in 5" :key="n" class="h-9 w-full" /></div>
    <AppEmpty v-else-if="!events.length" size="xs" :icon="failed ? 'i-lucide-cloud-alert' : 'i-lucide-activity'" :title="failed ? t('dataView.errorTitle') : t('dataSources.home.noEvents')" :actions="failed ? [{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: load }] : undefined" />
    <UTable
      v-else
      :data="events"
      :columns="columns"
      class="-mx-1"
      :ui="{ thead: 'bg-elevated/50', th: 'py-2 text-xs font-medium text-muted', td: 'py-2.5 text-sm', tr: 'cursor-pointer hover:bg-elevated/50' }"
      @select="openEvent"
    >
      <template #action-cell="{ row }">
        <span class="flex min-w-0 items-center gap-2">
          <span class="size-2 shrink-0 rounded-[2px]" :class="ACTIVITY_COLOR[kindOfAction(row.original.action) ?? 'connections']" />
          <span class="truncate font-medium text-highlighted">{{ format.actionLabel(row.original.action) }}</span>
          <UBadge v-if="row.original.outcome !== 'success'" :label="format.outcomeLabel(row.original.outcome)" :color="format.outcomeColor(row.original.outcome)" variant="subtle" size="xs" class="rounded-md" />
        </span>
      </template>
      <template #where-cell="{ row }"><span class="block max-w-56 truncate text-muted">{{ row.original.resource?.name || '–' }}</span></template>
      <template #who-cell="{ row }"><span class="block max-w-40 truncate">{{ row.original.actor.name }}</span></template>
      <template #occurred_at-cell="{ row }">
        <UTooltip :text="dateTime(row.original.occurred_at)"><span class="whitespace-nowrap text-muted">{{ relative(row.original.occurred_at) }}</span></UTooltip>
      </template>
    </UTable>
  </UCard>
</template>
