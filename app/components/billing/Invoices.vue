<!--
  Invoices and receipts (F24), newest first: number, date, plan and period, amount, status and the card. A short
  list inside Settings → Subscription (the platform keeps them all), so a plain table rather than a list page.
  Download PDF asks for Paddle's invoice (GET /billing/invoices/{id}/pdf, a short-lived link) and opens it in a new
  tab; with no PDF yet (url null) that invoice's button is switched off.
-->
<script setup lang="ts">
import type { Invoice } from '#shared/types/billing'

const props = defineProps<{ invoices: Invoice[] | null }>()
const { t } = useI18n()
const { currency, date } = useFormat()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const STATUS_COLOR = { paid: 'success', open: 'warning', failed: 'error', refunded: 'neutral' } as const
const shown = ref(6)
const rows = computed(() => props.invoices?.slice(0, shown.value) ?? [])

/** Invoices whose PDF isn't there yet, and the one being fetched (its button spins). */
const missing = ref(new Set<string>())
const fetching = ref<string | null>(null)
async function downloadPdf(invoice: Invoice) {
  fetching.value = invoice.id
  try {
    const { data } = await api.get<{ url: string | null }>(`/billing/invoices/${invoice.id}/pdf`)
    if (!data.url || !/^https:\/\//i.test(data.url)) {
      missing.value = new Set([...missing.value, invoice.id])
      toast.add({ title: t('billing.invoice.pdfMissing'), color: 'neutral', icon: 'i-lucide-file-x' })
      return
    }
    const url = data.url
    // Pop-up blockers may stop a tab opened after a wait: then a button in the toast opens it with a fresh click
    if (!window.open(url, '_blank', 'noopener,noreferrer'))
      toast.add({ title: t('billing.invoice.pdfReady'), color: 'neutral', icon: 'i-lucide-file-text', actions: [{ label: t('billing.invoice.pdfOpen'), color: 'neutral', variant: 'outline', onClick: () => void window.open(url, '_blank', 'noopener,noreferrer') }] })
  } catch (error) {
    handle(error)
  } finally {
    fetching.value = null
  }
}
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
            <th class="px-3 py-2"><span class="sr-only">{{ t('billing.invoice.pdf') }}</span></th>
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
            <td class="px-3 py-2 text-end">
              <UButton :label="t('billing.invoice.pdf')" icon="i-lucide-file-down" color="neutral" variant="ghost" size="xs" :loading="fetching === invoice.id" :disabled="missing.has(invoice.id) || (!!fetching && fetching !== invoice.id)" @click="downloadPdf(invoice)" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <UButton v-if="invoices.length > shown" :label="t('billing.invoice.more')" color="neutral" variant="link" size="xs" class="self-start px-0" @click="shown += 12" />
  </div>
</template>
