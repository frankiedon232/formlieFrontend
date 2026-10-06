<!--
  A webhook (locked card format, rule 21): a "last delivery" pill, status and ⋯ on top; its name
  (red flag when it is failing) and address; events, forms, deliveries and time taken in two
  columns; a divider, then the delivered share as a slim bar; who made it and 30 days of deliveries.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { Webhook } from '#shared/types/integrations'

const props = defineProps<{ item: Webhook; actions: DropdownMenuItem[][]; busy?: boolean }>()
const { t } = useI18n()
const { relative, number, percent } = useFormat()
const facts = computed(() => [
  { key: 'events', label: t('integrations.webhooks.col.events'), value: t('integrations.webhooks.eventsCount', { n: props.item.events.length }, props.item.events.length) },
  { key: 'forms', label: t('integrations.webhooks.col.forms'), value: props.item.forms.length ? t('integrations.webhooks.formsCount', { n: props.item.forms.length }, props.item.forms.length) : t('integrations.webhooks.allForms') },
  { key: 'deliveries', label: t('integrations.webhooks.col.deliveries'), value: number(props.item.deliveries_30d) },
  { key: 'time', label: t('apiService.kpi.time'), value: props.item.avg_ms == null ? '–' : t('dataSources.ms', { n: props.item.avg_ms }) },
])
</script>

<template>
  <article class="group relative flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md" :class="[busy ? 'pointer-events-none opacity-60' : '', item.enabled ? '' : 'opacity-75']" :aria-busy="busy || undefined">
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon :name="busy ? 'i-lucide-loader-circle' : 'i-lucide-clock'" class="size-3.5 shrink-0 text-muted" :class="busy ? 'animate-spin' : ''" />
        <span class="truncate">{{ item.last_delivery ? t('integrations.webhooks.lastDelivery', { when: relative(item.last_delivery.at) }) : t('integrations.webhooks.noDeliveries') }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <DataStatusBadge :status="item.status" :label="t(`integrations.webhooks.status.${item.status}`)" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <div class="mt-3 flex min-w-0 flex-col">
      <span class="flex min-w-0 items-center gap-1.5">
        <UIcon v-if="item.status === 'failing'" name="i-lucide-flag" class="size-4 shrink-0 text-error" />
        <span class="truncate text-base font-semibold text-highlighted">{{ item.name }}</span>
      </span>
      <p class="truncate font-mono text-xs text-muted" dir="ltr">{{ item.url }}</p>
    </div>

    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm text-default tabular-nums">{{ fact.value }}</dd>
      </div>
    </dl>

    <div class="mt-auto pt-4">
      <div class="border-t border-default pt-3">
        <div class="flex items-center justify-between text-xs">
          <span class="text-muted">{{ t('integrations.webhooks.kpi.delivered') }}</span>
          <span class="font-medium text-highlighted tabular-nums">{{ item.success_rate == null ? '–' : percent(item.success_rate, 0) }}</span>
        </div>
        <UProgress :model-value="Math.round((item.success_rate ?? 0) * 100)" size="xs" color="neutral" class="mt-1.5" />
      </div>
      <div class="mt-4 flex items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-2">
          <UAvatar :alt="item.created_by.name" size="2xs" />
          <span class="truncate text-xs text-muted">{{ item.created_by.name }}</span>
        </div>
        <ChartsSparkline :values="item.daily.map(day => day.count)" :width="72" :height="20" />
      </div>
    </div>
  </article>
</template>
