<!--
  The card renewals are charged to (F24): brand, last four digits and expiry only. Paddle, our payment provider and
  merchant of record (owner 2026-10-13), keeps the card: it can be replaced in Paddle's window (Update card, a
  checkout with purpose add_card) but not removed (DELETE /billing/payment-method answers 409 managed_by_provider).
-->
<script setup lang="ts">
import type { BillingOverview } from '#shared/types/billing'

const props = defineProps<{ overview: BillingOverview }>()
const { t } = useI18n()
const billing = useBilling()

const card = computed(() => props.overview.subscription.payment_method)
const ICONS = { visa: 'i-simple-icons-visa', mastercard: 'i-simple-icons-mastercard', amex: 'i-simple-icons-americanexpress', discover: 'i-simple-icons-discover', other: 'i-lucide-credit-card' } as const
const NAMES = { visa: 'Visa', mastercard: 'Mastercard', amex: 'American Express', discover: 'Discover', other: '' } as const
const expiringSoon = computed(() => {
  if (!card.value) return false
  const end = Date.UTC(card.value.exp_year, card.value.exp_month, 0)
  return end - Date.now() < 45 * 86_400_000
})

const { busy, run } = useBusy()
const update = () => run(() => billing.addCard())
</script>

<template>
  <div class="flex flex-col gap-3">
    <div v-if="card" class="flex flex-wrap items-center gap-3 rounded-lg border border-default p-3">
      <span class="flex h-9 w-12 items-center justify-center rounded-md border border-default bg-elevated"><UIcon :name="ICONS[card.brand]" class="size-6" /></span>
      <span class="flex min-w-0 flex-1 flex-col">
        <span class="text-sm font-medium text-highlighted">{{ NAMES[card.brand] }} •••• {{ card.last4 }}</span>
        <span class="text-xs" :class="expiringSoon ? 'text-warning' : 'text-muted'">{{ t('billing.card.expires', { date: `${String(card.exp_month).padStart(2, '0')}/${card.exp_year}` }) }}<template v-if="expiringSoon"> · {{ t('billing.card.expiringSoon') }}</template></span>
      </span>
      <UButton :label="t('billing.card.update')" icon="i-lucide-refresh-cw" color="neutral" variant="outline" size="sm" :loading="busy" @click="update" />
    </div>
    <div v-else class="flex flex-wrap items-center gap-3 rounded-lg border border-dashed border-accented p-3">
      <UIcon name="i-lucide-credit-card" class="size-5 text-muted" />
      <span class="min-w-0 flex-1 text-sm text-muted">{{ t('billing.card.none') }}</span>
      <UButton :label="t('billing.addCard')" icon="i-lucide-plus" color="neutral" variant="outline" size="sm" :loading="busy" @click="update" />
    </div>
    <p class="flex items-start gap-1.5 text-xs text-muted"><UIcon name="i-lucide-lock" class="mt-0.5 size-3.5 shrink-0" />{{ t('billing.card.secure') }}</p>
  </div>
</template>
