<!--
  A form storing its responses in a database (locked card format, rule 21): "last delivery" pill,
  status and ⋯; the form (red flag when failing) and its connection; table, how rows are written,
  pending and failed in two columns; a divider, then Delivered (30 days) with a black bar; the
  engine, whether Formalie created the table, and the 30-day trend.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { DestinationRow } from '#shared/types/destinations'

const props = defineProps<{ destination: DestinationRow; actions: DropdownMenuItem[][] }>()
const { t } = useI18n()
const { relative, number } = useFormat()
const share = computed(() => {
  const total = props.destination.sent_30d + props.destination.failed + props.destination.pending
  return total ? Math.round((props.destination.sent_30d / total) * 100) : null
})
const facts = computed(() => [
  { key: 'table', label: t('destinations.col.table'), value: `${props.destination.table.schema}.${props.destination.table.name}`, ltr: true },
  { key: 'write', label: t('destinations.options.writeLegend'), value: props.destination.table.created ? t('destinations.options.write.standard') : t(`destinations.options.write.${props.destination.settings.write_mode}`) },
  { key: 'pending', label: t('destinations.kpi.pending'), value: number(props.destination.pending) },
  { key: 'failed', label: t('destinations.kpi.failed'), value: number(props.destination.failed), warn: props.destination.failed > 0 },
])
</script>

<template>
  <article class="group flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md">
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon name="i-lucide-send" class="size-3.5 shrink-0 text-muted" />
        <span class="truncate">{{ destination.last_delivery_at ? t('destinations.card.last', { when: relative(destination.last_delivery_at) }) : t('destinations.card.none') }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <DataStatusBadge :status="destination.status" :label="t(`destinations.status.${destination.status}`)" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <div class="mt-3 flex min-w-0 flex-col">
      <div class="flex min-w-0 items-center gap-1.5">
        <UIcon v-if="destination.status === 'failing'" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('dataSources.needsLook')" />
        <NuxtLink :to="{ query: { destination: destination.id } }" class="truncate text-base font-semibold text-highlighted hover:underline focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">{{ destination.form.name }}</NuxtLink>
      </div>
      <p class="truncate text-sm text-muted">{{ destination.datasource.name }}</p>
    </div>

    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm" :class="[fact.ltr ? 'text-start font-mono text-xs leading-5' : 'tabular-nums', fact.warn ? 'text-error' : 'text-default']" :dir="fact.ltr ? 'ltr' : undefined">{{ fact.value }}</dd>
      </div>
    </dl>

    <div class="mt-auto pt-4">
      <div class="border-t border-default pt-3">
        <div class="mb-1.5 flex items-center justify-between text-xs">
          <span class="text-muted">{{ t('destinations.kpi.deliveredShare') }}</span>
          <span class="font-medium text-highlighted tabular-nums">{{ share === null ? '–' : `${share}%` }}</span>
        </div>
        <div class="h-1.5 overflow-hidden rounded-full bg-elevated" role="presentation">
          <div class="h-full rounded-full bg-inverted" :style="{ width: `${share ?? 0}%` }" />
        </div>
      </div>
      <div class="mt-4 flex items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-2">
          <DatasourcesEngineLogo :engine="destination.datasource.engine" size="sm" />
          <UBadge :label="destination.table.created ? t('destinations.table.created') : t('destinations.table.yours')" color="neutral" variant="outline" size="sm" class="rounded-md" />
        </div>
        <ChartsSparkline :values="destination.daily.map(day => day.count)" :width="72" :height="20" />
      </div>
    </div>
  </article>
</template>
