<!--
  Dashboard → Recent responses (F21, the design's "Recent Tasks" table): the newest responses across the forms the
  person may see: who, which form, review status, how complete (slim black bar), when; a row opens the response in
  its form's list. "All responses" leads to the full list.
-->
<script setup lang="ts">
import type { ResponseRow } from '#shared/types/responses'

const props = defineProps<{ folder?: string; owner?: string }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { relative, number } = useFormat()
const { can } = useCan()

const rows = ref<ResponseRow[] | null>(null)
async function load() {
  if (!can('responses.view')) return void (rows.value = [])
  try {
    rows.value = (await api.list<ResponseRow>('/responses', { page_size: 6, 'filter[folder_id]': props.folder, 'filter[owner_id]': props.owner }, { background: true })).data
  } catch (error) {
    handle(error, { silent: true })
    rows.value = []
  }
}
defineExpose({ reload: load })
watch(() => [props.folder, props.owner], load, { immediate: true })

const who = (row: ResponseRow) => row.respondent.title || row.respondent.name || row.respondent.email || t('dashboard.recent.anonymous')
const initials = (row: ResponseRow) =>
  who(row)
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(word => word[0]!.toUpperCase())
    .join('')
const percent = (row: ResponseRow) => (row.questions ? Math.round((row.answered / row.questions) * 100) : 100)
const open = (row: ResponseRow) => navigateTo({ path: `/forms/${row.form.id}/responses`, query: { response: row.id } })
</script>

<template>
  <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
    <div class="flex items-center gap-2">
      <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.recent.title') }}</h2>
      <UButton :label="t('dashboard.recent.all')" trailing-icon="i-lucide-arrow-right" color="neutral" variant="outline" size="xs" class="ms-auto [&_svg]:rtl:rotate-180" to="/responses" />
    </div>
    <div v-if="!rows" class="flex flex-col gap-2"><USkeleton v-for="n in 5" :key="n" class="h-11 w-full" /></div>
    <AppEmpty v-else-if="!rows.length" size="sm" icon="i-lucide-inbox" :title="t('dashboard.recent.none')" :description="t('dashboard.recent.noneDesc')" />
    <div v-else class="overflow-x-auto rounded-lg border border-default">
      <table class="w-full min-w-[34rem] text-sm">
        <thead class="bg-elevated/50 text-xs text-muted">
          <tr>
            <th class="px-3 py-2 text-start font-medium">{{ t('dashboard.recent.who') }}</th>
            <th class="px-3 py-2 text-start font-medium">{{ t('dashboard.recent.form') }}</th>
            <th class="px-3 py-2 text-start font-medium">{{ t('dashboard.recent.status') }}</th>
            <th class="px-3 py-2 text-start font-medium">{{ t('dashboard.recent.complete') }}</th>
            <th class="px-3 py-2 text-end font-medium">{{ t('dashboard.recent.when') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-default">
          <tr v-for="row in rows" :key="row.id" class="cursor-pointer transition-colors hover:bg-elevated/50" tabindex="0" @click="open(row)" @keydown.enter="open(row)">
            <td class="px-3 py-2">
              <span class="flex min-w-0 items-center gap-2">
                <span class="flex size-7 shrink-0 items-center justify-center rounded-full bg-elevated text-[11px] font-medium text-default">{{ initials(row) }}</span>
                <span class="flex min-w-0 flex-col">
                  <span class="truncate text-highlighted">{{ who(row) }}</span>
                  <span class="text-[11px] text-muted">#{{ row.number }}</span>
                </span>
              </span>
            </td>
            <td class="max-w-48 truncate px-3 py-2 text-default">{{ row.form.name }}</td>
            <td class="px-3 py-2"><DataStatusBadge :status="row.status" /></td>
            <td class="px-3 py-2">
              <span class="flex items-center gap-2">
                <span class="h-1.5 w-24 overflow-hidden rounded-full bg-elevated"><span class="block h-full rounded-full bg-inverted" :style="{ width: `${percent(row)}%` }" /></span>
                <span class="text-xs text-muted tabular-nums">{{ number(percent(row)) }}%</span>
              </span>
            </td>
            <td class="px-3 py-2 text-end text-xs whitespace-nowrap text-muted">{{ relative(row.submitted_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </UCard>
</template>
