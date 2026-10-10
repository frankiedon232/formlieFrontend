<!--
  Invoices and receipts (F24), newest first: number, date, plan and period, amount, status and the card. A short
  list inside Settings → Subscription (the platform keeps them all), so a plain table rather than a list page.
-->
<script setup lang="ts">
import type { Invoice } from '#shared/types/billing'

const props = defineProps<{ invoices: Invoice[] | null }>()
const { t } = useI18n()
const { currency, date } = useFormat()
const STATUS_COLOR = { paid: 'success', open: 'warning', failed: 'error', refunded: 'neutral' } as const
const shown = ref(6)
const rows = computed(() => props.invoices?.slice(0, shown.value) ?? [])
</script>

<template>
  <div v-if="!invoices" class="flex flex-col gap-2"><USkeleton v-for="n in 3" :key="n" class="h-10 rounded-md" /></div>
  <AppEmpty v-else-if="!invoices.length" size="sm" icon="i-lucide-receipt-text" :title="t('billing.invoice.none')" :description="t('billing.invoice.noneDesc')" />
  <div v-else class="flex flex-col gap-2">
    <div class="overflow-x-auto rounded-lg border border-default">
      <table class="w-full min-w-[36rem] text-sm">
        <thead class="bg-elevated/50 text-xs text-muted">
          <tr>
            <th class="px-3 py-2 text-start font-medium">{{ t('billing.invoice.number') }}</th>
            <th class="px-3 py-2 text-start font-medium">{{ t('billing.invoice.date') }}</th>
            <th class="px-3 py-2 text-start font-medium">{{ t('billing.invoice.plan') }}</th>
            <th class="px-3 py-2 text-end font-medium">{{ t('billing.invoice.amount') }}</th>
            <th class="px-3 py-2 text-start font-medium">{{ t('billing.invoice.status') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-default">
          <tr v-for="invoice in rows" :key="invoice.id" class="transition-colors hover:bg-elevated/40">
            <td class="px-3 py-2 font-mono text-xs text-highlighted">{{ invoice.number }}</td>
            <td class="px-3 py-2 text-default">{{ date(invoice.issued_at) }}</td>
            <td class="px-3 py-2">
              <span class="text-default">{{ t(`billing.plan.${invoice.plan}.name`) }}</span>
              <span class="block text-xs text-muted">{{ date(invoice.period_start) }} → {{ date(invoice.period_end) }}</span>
            </td>
            <td class="px-3 py-2 text-end text-highlighted tabular-nums">{{ currency(invoice.amount, invoice.currency) }}</td>
            <td class="px-3 py-2">
              <UBadge :label="t(`billing.invoice.state.${invoice.status}`)" :color="STATUS_COLOR[invoice.status]" variant="subtle" size="sm" />
              <span v-if="invoice.card" class="block text-xs text-muted">{{ invoice.card }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <UButton v-if="invoices.length > shown" :label="t('billing.invoice.more')" color="neutral" variant="link" size="xs" class="self-start px-0" @click="shown += 12" />
  </div>
</template>
