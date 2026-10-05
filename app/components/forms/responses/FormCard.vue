<!--
  A form on the Responses page (grouped by form; locked card format, CLAUDE.md rule 21): last
  response pill, form status and ⋯ on top; the form name (red flag = new responses to review) with
  its folder; responses and three review counts in two columns, the status the list is about
  (`focus`, sidebar New / Approved…) first and in bold; Reviewed with a black bar (how
  much of it the team has looked at); owner, link key, a 30-day sparkline and the new count below.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ResponseFormRow, ResponseStatus } from '#shared/types/responses'

const props = withDefaults(defineProps<{ row: ResponseFormRow; actions: DropdownMenuItem[][]; focus?: ResponseStatus; to?: string }>(), { focus: 'new', to: undefined })
const { t } = useI18n()
const { relative, number, percent } = useFormat()
const reviewed = computed(() => (props.row.total ? (props.row.total - props.row.status_counts.new) / props.row.total : 0))
const facts = computed(() => {
  const statuses = [props.focus, ...(['new', 'approved', 'rejected'] as const).filter(status => status !== props.focus)].slice(0, 3)
  return [
    { key: 'total' as const, label: t('forms.col.responses'), value: number(props.row.total), strong: true },
    ...statuses.map(status => ({ key: status, label: t(`status.${status}`), value: number(props.row.status_counts[status]), strong: status === props.focus && props.row.status_counts[status] > 0 })),
  ]
})
</script>

<template>
  <article class="group flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md">
    <!-- Last response · status · menu -->
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon name="i-lucide-clock-3" class="size-3.5 shrink-0 text-muted" />
        <span class="truncate">{{ row.last_at ? relative(row.last_at) : '–' }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <DataStatusBadge :status="row.status" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <!-- Form and folder -->
    <div class="mt-3 flex min-w-0 items-center gap-1.5">
      <UTooltip v-if="row.status_counts.new" :text="t('responses.byForm.newWaiting', { n: number(row.status_counts.new) }, row.status_counts.new)">
        <UIcon name="i-lucide-flag" class="size-4 shrink-0 text-error" :aria-label="t('responses.byForm.newWaiting', { n: row.status_counts.new }, row.status_counts.new)" />
      </UTooltip>
      <NuxtLink :to="to ?? `/forms/${row.id}/responses`" class="truncate text-base font-semibold text-highlighted hover:underline focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">{{ row.name }}</NuxtLink>
    </div>
    <p class="flex min-w-0 items-center gap-1.5 text-sm text-muted">
      <UIcon name="i-lucide-folder" class="size-3.5 shrink-0" />
      <span class="truncate">{{ row.folder?.name ?? t('forms.noFolder') }}</span>
      <FormsStorageMark :storage="row.storage" />
    </p>

    <!-- Counts (two columns) -->
    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="flex items-center gap-1.5 truncate text-[11px] text-muted">
          <span v-if="fact.key !== 'total'" class="size-1.5 rounded-[2px]" :class="RESPONSE_STATUS_META[fact.key].fill" />{{ fact.label }}
        </dt>
        <dd class="h-5 truncate text-sm tabular-nums" :class="fact.strong ? 'font-semibold text-highlighted' : 'text-default'">{{ fact.value }}</dd>
      </div>
    </dl>

    <!-- Reviewed so far (the design's Progress) -->
    <div class="mt-auto pt-4">
      <div class="border-t border-default pt-3">
        <div class="mb-1.5 flex items-center justify-between text-xs">
          <span class="text-muted">{{ t('responses.byForm.reviewed') }}</span>
          <span class="font-medium text-highlighted tabular-nums">{{ percent(reviewed) }}</span>
        </div>
        <div class="h-1.5 overflow-hidden rounded-full bg-elevated" role="presentation">
          <div class="h-full rounded-full bg-inverted" :style="{ width: `${reviewed * 100}%` }" />
        </div>
      </div>

      <!-- Owner, key, trend -->
      <div class="mt-4 flex items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-2">
          <UAvatar :alt="row.owner.name" size="xs" />
          <span class="truncate font-mono text-xs text-muted">{{ row.custom_link || row.public_key }}</span>
        </div>
        <ChartsSparkline :values="row.daily" :width="72" :height="20" />
      </div>
    </div>
  </article>
</template>
