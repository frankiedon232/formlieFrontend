<!--
  The payment step (F24). Card details are only ever typed on the processor's (Payoneer's) secure checkout,
  never in Formalie. With the processor connected, the session has its address and the step hands over to it;
  until then (the mock) this dialog is a clearly marked test step: pay or save a test card, or try a declined
  payment. Formalie keeps only the brand, the last four digits, the expiry and the processor's reference.
-->
<script setup lang="ts">
import type { CheckoutSession } from '#shared/types/billing'

const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { currency } = useFormat()
const billing = useBilling()

// The dialog closes first and lets go of the session once it is gone (clearing both at once left it half closed)
const open = ref(false)
const session = ref<CheckoutSession | null>(null)
watch(billing.checkout, value => {
  if (!value) return
  session.value = value
  open.value = true
})
function released() {
  billing.checkout.value = null
  session.value = null
}
const brand = ref<'visa' | 'mastercard' | 'amex' | 'discover'>('visa')
const brands = [
  { value: 'visa', label: 'Visa', icon: 'i-simple-icons-visa' },
  { value: 'mastercard', label: 'Mastercard', icon: 'i-simple-icons-mastercard' },
  { value: 'amex', label: 'American Express', icon: 'i-simple-icons-americanexpress' },
  { value: 'discover', label: 'Discover', icon: 'i-simple-icons-discover' },
]

// A real processor page: hand over (it brings people back to Settings → Subscription)
watch(session, value => value?.url && navigateTo(value.url, { external: true }))

const { busy, run } = useBusy()
async function finish(outcome: 'paid' | 'declined') {
  const current = session.value
  if (!current) return
  const ok = await run(async () => {
    await api.post(`/billing/checkout/${current.id}/complete`, { outcome, brand: brand.value })
    return true
  })
  open.value = false
  if (ok) {
    toast.add({ title: current.purpose === 'add_card' ? t('billing.cardSaved') : t('billing.paid', { plan: t(`billing.plan.${current.plan}.name`) }), color: 'success', icon: 'i-lucide-badge-check' })
    billing.invoices.value = null
  }
  try {
    await billing.load({ invoices: true })
  } catch (error) {
    handle(error, { silent: true })
  }
}
</script>

<template>
  <AppModal v-model:open="open" :title="session?.purpose === 'add_card' ? t('billing.checkout.cardTitle') : t('billing.checkout.title')" :description="t('billing.checkout.desc')" keep-open @after:leave="released">
    <template #body>
      <div v-if="session" class="flex flex-col gap-4">
        <div v-if="session.purpose === 'subscribe'" class="flex items-center justify-between gap-3 rounded-lg border border-default p-3">
          <span class="flex flex-col">
            <span class="text-sm font-medium text-highlighted">{{ t(`billing.plan.${session.plan}.name`) }}</span>
            <span class="text-xs text-muted">{{ t(`billing.periodName.${session.period}`) }}</span>
          </span>
          <span class="text-lg font-semibold text-highlighted tabular-nums">{{ currency(session.amount, session.currency) }}</span>
        </div>
        <p v-else class="text-sm text-default">{{ t('billing.checkout.cardDesc') }}</p>

        <div class="flex flex-col gap-3 rounded-lg border border-dashed border-accented bg-elevated/40 p-3">
          <p class="flex items-start gap-2 text-xs text-muted"><UIcon name="i-lucide-flask-conical" class="mt-0.5 size-3.5 shrink-0" />{{ t('billing.checkout.testNote') }}</p>
          <UFormField :label="t('billing.checkout.testCard')">
            <USelect v-model="brand" :items="brands" :icon="brands.find(item => item.value === brand)?.icon" class="w-full sm:max-w-xs" />
          </UFormField>
        </div>
        <p class="flex items-start gap-1.5 text-xs text-muted"><UIcon name="i-lucide-lock" class="mt-0.5 size-3.5 shrink-0" />{{ t('billing.checkout.secure') }}</p>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full flex-wrap justify-between gap-2">
        <UButton :label="t('billing.checkout.decline')" icon="i-lucide-credit-card" color="neutral" variant="ghost" :disabled="busy" @click="finish('declined')" />
        <div class="flex gap-2">
          <UButton :label="t('common.cancel')" color="neutral" variant="ghost" :disabled="busy" @click="open = false" />
          <UButton :label="session?.purpose === 'add_card' ? t('billing.checkout.saveCard') : t('billing.checkout.pay', { amount: session ? currency(session.amount, session.currency) : '' })" icon="i-lucide-lock" color="neutral" :loading="busy" @click="finish('paid')" />
        </div>
      </div>
    </template>
  </AppModal>
</template>
