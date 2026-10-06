<!--
  A webhook delivery (locked card format, rule 21): a "when" pill, result and ⋯ on top; the event as
  the title (red flag when it failed for good) and the webhook; status code, tries, time and form in
  two columns; a divider, then the address; the delivery's id at the bottom.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { WebhookDelivery } from '#shared/types/integrations'
import { eventLabelKey } from '#shared/utils/integrations/webhooks'

const props = defineProps<{ item: WebhookDelivery; actions: DropdownMenuItem[][]; busy?: boolean }>()
const { t } = useI18n()
const { relative } = useFormat()
const facts = computed(() => [
  { key: 'code', label: t('integrations.webhooks.col.code'), value: props.item.status_code == null ? '–' : String(props.item.status_code) },
  { key: 'tries', label: t('integrations.webhooks.col.tries'), value: String(props.item.attempts) },
  { key: 'time', label: t('apiService.kpi.time'), value: props.item.duration_ms == null ? '–' : t('dataSources.ms', { n: props.item.duration_ms }) },
  { key: 'form', label: t('integrations.webhooks.col.form'), value: props.item.form?.name ?? '–' },
])
</script>

<template>
  <article class="group relative flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md" :class="busy ? 'pointer-events-none opacity-60' : ''" :aria-busy="busy || undefined">
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon :name="busy ? 'i-lucide-loader-circle' : 'i-lucide-clock'" class="size-3.5 shrink-0 text-muted" :class="busy ? 'animate-spin' : ''" />
        <span class="truncate">{{ relative(item.at) }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <DataStatusBadge :status="item.status" :label="t(`integrations.webhooks.delivery.${item.status}`)" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <div class="mt-3 flex min-w-0 flex-col">
      <span class="flex min-w-0 items-center gap-1.5">
        <UIcon v-if="item.status === 'failed'" name="i-lucide-flag" class="size-4 shrink-0 text-error" />
        <span class="truncate text-base font-semibold text-highlighted">{{ t(eventLabelKey(item.event)) }}</span>
        <UBadge v-if="item.test" :label="t('integrations.webhooks.test')" color="neutral" variant="soft" size="sm" class="rounded-md" />
      </span>
      <p class="truncate text-sm text-muted">{{ item.webhook.name }}</p>
    </div>

    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm text-default tabular-nums">{{ fact.value }}</dd>
      </div>
    </dl>

    <div class="mt-auto pt-4">
      <p class="truncate border-t border-default pt-3 font-mono text-xs text-muted" dir="ltr">{{ item.webhook.url }}</p>
      <div class="mt-4 flex items-center justify-between gap-2">
        <code class="truncate font-mono text-[11px] text-muted">{{ item.event }}</code>
        <span v-if="item.next_retry_at" class="flex shrink-0 items-center gap-1 text-xs text-warning"><UIcon name="i-lucide-refresh-cw" class="size-3.5" />{{ relative(item.next_retry_at) }}</span>
      </div>
    </div>
  </article>
</template>
