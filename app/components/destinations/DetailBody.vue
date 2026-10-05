<!--
  Destination panel body: progress of earlier responses being sent; fact tiles; chips (All ·
  Deliveries · Columns · New fields); the deliveries; which column each answer or response fact
  goes in; fields added to the form since, with the columns Formalie would add (and the SQL).
-->
<script setup lang="ts">
import type { DestinationDetail } from '#shared/types/destinations'
import { addColumnSql, viewSql } from '#shared/utils/datasources/tables'

const props = defineProps<{ destination: DestinationDetail; refreshKey: number; busy: boolean }>()
const emit = defineEmits<{ addColumns: [keys: string[]]; retried: [] }>()
const { t } = useI18n()
const { relative, number, date } = useFormat()

type Group = 'all' | 'deliveries' | 'columns' | 'fields'
const group = ref<Group>('all')
const groups = computed(() => [
  { key: 'all' as const, icon: 'i-lucide-layout-grid' },
  { key: 'deliveries' as const, icon: 'i-lucide-send' },
  { key: 'columns' as const, icon: 'i-lucide-columns-3' },
  ...(props.destination.unmapped_fields.length ? [{ key: 'fields' as const, icon: 'i-lucide-list-plus' }] : []),
])
const show = (key: Group) => group.value === 'all' || group.value === key

const facts = computed(() => [
  { label: t('destinations.kpi.sent30'), value: number(props.destination.sent_30d) },
  { label: t('destinations.kpi.pending'), value: number(props.destination.pending) },
  { label: t('destinations.kpi.failed'), value: number(props.destination.failed) },
  { label: t('destinations.kpi.last'), value: props.destination.last_delivery_at ? relative(props.destination.last_delivery_at) : '–' },
  { label: t('destinations.kpi.notSent'), value: number(props.destination.not_sent) },
  { label: t('destinations.kpi.since'), value: date(props.destination.covers_from) },
])
const job = computed(() => props.destination.backfill)
const percent = computed(() => (job.value && job.value.total ? Math.round((job.value.done / job.value.total) * 100) : 100))
const sourceLabel = (column: DestinationDetail['columns'][number]) =>
  !column.source ? t('destinations.columns.nothing') : column.source.kind === 'meta' ? t(`destinations.meta.${column.source.key}`) : (props.destination.fields.find(field => field.key === column.source!.key)?.label ?? column.source.key)
// A view naming each column after its question, for their own systems (tables Formalie created).
const view = computed(() => viewSql(props.destination.datasource.engine, props.destination.table.schema, props.destination.table.name, props.destination.columns, new Map(props.destination.fields.map(field => [field.key, field.label]))))
const toast = useToast()
const { copy } = useClipboard({ legacy: true })
function copyView() {
  void copy(view.value)
  toast.add({ title: t('dataSources.grant.copied'), color: 'success', icon: 'i-lucide-check' })
}
const addSql = computed(() => props.destination.unmapped_fields.map(field => addColumnSql(props.destination.datasource.engine, props.destination.table.schema, props.destination.table.name, field)).join('\n'))
</script>

<template>
  <div class="flex flex-col gap-5">
    <div v-if="job && job.status === 'running'" class="flex flex-col gap-2 rounded-lg border border-default p-3" role="status">
      <div class="flex items-center justify-between gap-2 text-sm">
        <span class="font-medium text-highlighted">{{ t('destinations.backfill.running', { done: number(job.done), total: number(job.total) }) }}</span>
        <span class="text-muted tabular-nums">{{ percent }}%</span>
      </div>
      <UProgress :model-value="percent" color="neutral" size="sm" />
    </div>
    <UAlert v-else-if="job && job.status === 'done'" icon="i-lucide-circle-check" color="success" variant="subtle" :title="t('destinations.backfill.done', { n: number(job.total) }, job.total)" />

    <dl class="grid grid-cols-2 gap-2 sm:grid-cols-3">
      <div v-for="fact in facts" :key="fact.label" class="flex min-w-0 flex-col gap-0.5 rounded-lg border border-default px-3 py-2">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="truncate text-sm font-medium text-highlighted tabular-nums">{{ fact.value }}</dd>
      </div>
    </dl>

    <AppChipScroller :label="t('dataSources.detail.groups')">
      <button
        v-for="item in groups"
        :key="item.key"
        type="button"
        data-chip
        :aria-pressed="group === item.key"
        class="inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-(--ui-border-inverted)"
        :class="group === item.key ? 'bg-default text-highlighted shadow-xs ring-1 ring-(--ui-border)' : 'text-muted hover:text-highlighted'"
        @click="group = item.key"
      >
        <UIcon :name="item.icon" class="size-3.5" />
        {{ t(`destinations.detail.${item.key}`) }}
      </button>
    </AppChipScroller>

    <section v-if="destination.unmapped_fields.length" v-show="show('fields')" class="flex flex-col gap-2">
      <h3 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('destinations.detail.fields') }}</h3>
      <UAlert icon="i-lucide-list-plus" color="warning" variant="subtle" :title="t('destinations.detail.fieldsTitle', { n: destination.unmapped_fields.length }, destination.unmapped_fields.length)" :description="t('destinations.detail.fieldsDesc')" />
      <ul class="divide-y divide-default rounded-lg border border-default">
        <li v-for="field in destination.unmapped_fields" :key="field.key" class="flex items-center gap-2 px-3 py-2 text-sm">
          <span class="min-w-0 flex-1 truncate text-highlighted">{{ field.label }}</span>
          <code class="font-mono text-xs text-muted" dir="ltr">{{ field.column }} {{ field.type }}</code>
        </li>
      </ul>
      <pre class="overflow-x-auto rounded-lg border border-default px-3 py-2 font-mono text-[11px] text-default" dir="ltr" tabindex="0">{{ addSql }}</pre>
      <UButton :label="t('destinations.detail.addColumns', { n: destination.unmapped_fields.length }, destination.unmapped_fields.length)" icon="i-lucide-plus" color="neutral" size="sm" class="w-fit" :loading="busy" @click="emit('addColumns', destination.unmapped_fields.map(field => field.key))" />
    </section>

    <section v-show="show('deliveries')" class="flex flex-col gap-2">
      <h3 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('destinations.detail.deliveries') }}</h3>
      <DestinationsDeliveries :destination-id="destination.id" :form-id="destination.form.id" :refresh-key="refreshKey" @retried="emit('retried')" />
    </section>

    <section v-show="show('columns')" class="flex flex-col gap-2">
      <h3 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('destinations.detail.columns') }}</h3>
      <ul class="divide-y divide-default rounded-lg border border-default">
        <li v-for="column in destination.columns" :key="column.column" class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 px-3 py-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_7rem]">
          <code class="truncate font-mono text-xs text-highlighted" dir="ltr">{{ column.column }}</code>
          <span class="hidden truncate text-sm sm:block" :class="column.source ? 'text-default' : 'text-dimmed'">{{ sourceLabel(column) }}</span>
          <code class="truncate text-end font-mono text-[11px] text-muted" dir="ltr">{{ column.type }}</code>
        </li>
      </ul>
      <UCollapsible v-if="destination.table.created" class="flex flex-col gap-2">
        <UButton :label="t('destinations.detail.viewTitle')" icon="i-lucide-eye" trailing-icon="i-lucide-chevron-down" color="neutral" variant="outline" size="sm" class="w-fit" />
        <template #content>
          <div class="flex flex-col gap-2 pt-1">
            <p class="text-xs text-muted">{{ t('destinations.detail.viewDesc') }}</p>
            <div class="overflow-hidden rounded-lg border border-default">
              <div class="flex justify-end bg-elevated/50 px-2 py-1">
                <UButton icon="i-lucide-copy" color="neutral" variant="ghost" size="xs" :aria-label="t('common.copy')" @click="copyView" />
              </div>
              <pre class="max-h-72 overflow-auto px-3 py-2 font-mono text-[11px] leading-relaxed text-default" dir="ltr" tabindex="0">{{ view }}</pre>
            </div>
          </div>
        </template>
      </UCollapsible>
    </section>
  </div>
</template>
