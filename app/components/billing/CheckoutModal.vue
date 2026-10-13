<!--
  The payment step (F24; Paddle, our merchant of record, owner 2026-10-13). Card details are typed only in Paddle's
  own window, opened with Paddle.js (loaded once from Paddle's CDN): Environment.set('sandbox') in the sandbox,
  Initialize with the session's client token, then Checkout.open with its transaction (a payment, or a card update).
  The browser never decides that something was paid: when Paddle's window completes or closes, the dialog asks the
  backend for the checkout until Paddle's signed notification has completed it (shared/utils/billing/checkout.ts).
  Without a client token (the mock) this dialog is a clearly marked test step: pay or save a test card, or try a
  declined payment. Formalie keeps only the brand, the last four digits, the expiry and Paddle's reference.
-->
<script lang="ts">
import type { CheckoutSession, CheckoutStatus } from '#shared/types/billing'
import { waitForCheckout } from '#shared/utils/billing/checkout'
// Paddle.js is one per page: loaded once, initialised once, shared by every instance of this dialog (it sits on both
// Subscription and Plans). Each checkout points `onPaddleEvent` at itself.
interface PaddleEvent { name?: string }
interface PaddleJs {
  Environment: { set: (environment: string) => void }
  Initialize: (options: { token: string; eventCallback: (event: PaddleEvent) => void }) => void
  Checkout: { open: (options: { transactionId: string }) => void; close: () => void }
}

const PADDLE_JS = 'https://cdn.paddle.com/paddle/v2/paddle.js'
let paddleLoading: Promise<PaddleJs> | null = null
let paddleReady = false
let onPaddleEvent: ((name: string) => void) | null = null
const paddleOf = () => (window as unknown as { Paddle?: PaddleJs }).Paddle
function loadPaddle(): Promise<PaddleJs> {
  paddleLoading ??= new Promise<PaddleJs>((resolve, reject) => {
    if (paddleOf()) return resolve(paddleOf()!)
    const script = document.createElement('script')
    script.src = PADDLE_JS
    script.async = true
    script.onload = () => (paddleOf() ? resolve(paddleOf()!) : reject(new Error('paddle')))
    script.onerror = () => {
      script.remove()
      paddleLoading = null
      reject(new Error('paddle'))
    }
    document.head.appendChild(script)
  })
  return paddleLoading
}
</script>

<script setup lang="ts">

const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { currency } = useFormat()
const billing = useBilling()

// The dialog closes first and lets go of the session once it is gone (clearing both at once left it half closed)
const open = ref(false)
const session = ref<CheckoutSession | null>(null)
/** test: the mock's step · confirming: waiting for Paddle's notification after its window. */
const phase = ref<'test' | 'confirming'>('test')
function released() {
  billing.checkout.value = null
  session.value = null
}

async function openPaddle(current: CheckoutSession) {
  const { provider } = current
  let completed = false
  onPaddleEvent = name => {
    if (name === 'checkout.completed') {
      completed = true
      paddleOf()?.Checkout.close()
      void confirm(current, true)
    } else if (name === 'checkout.closed' && !completed) void confirm(current, false)
  }
  try {
    const paddle = await loadPaddle()
    if (!paddleReady) {
      if (provider.environment === 'sandbox') paddle.Environment.set('sandbox')
      paddle.Initialize({ token: provider.client_token!, eventCallback: event => event.name && onPaddleEvent?.(event.name) })
      paddleReady = true
    }
    paddle.Checkout.open({ transactionId: provider.transaction_id! })
  } catch {
    // Paddle.js didn't load (blocked or offline): Paddle's own checkout link still works
    if (current.url) return navigateTo(current.url, { external: true })
    toast.add({ title: t('billing.checkout.unavailable'), color: 'error', icon: 'i-lucide-circle-alert' })
    released()
  }
}

/** After Paddle's window: ask the backend (never the browser) whether Paddle completed it. */
async function confirm(current: CheckoutSession, paid: boolean) {
  onPaddleEvent = null
  phase.value = 'confirming'
  if (paid) open.value = true
  let status: CheckoutStatus = 'open'
  try {
    status = await waitForCheckout(
      async () => (await api.get<CheckoutSession>(`/billing/checkout/${current.id}`, undefined, { background: true })).data.status,
      // Closed without paying: one short look in case the payment finished just before
      paid ? {} : { forMs: 6_000 },
    )
    if (status === 'completed') toast.add({ title: current.purpose === 'add_card' ? t('billing.cardSaved') : t('billing.paid', { plan: t(`billing.plan.${current.plan}.name`) }), color: 'success', icon: 'i-lucide-badge-check' })
    else if (status === 'open' && paid) toast.add({ title: t('billing.checkout.pending'), description: t('billing.checkout.pendingDesc'), color: 'warning', icon: 'i-lucide-hourglass', duration: 10_000 })
    if (status === 'completed' || paid) {
      billing.invoices.value = null
      await billing.load({ invoices: true })
    }
  } catch (error) {
    handle(error, { silent: true })
  } finally {
    if (open.value) open.value = false
    else released()
  }
}

watch(billing.checkout, value => {
  if (!value) return
  session.value = value
  if (value.provider?.client_token && value.provider.transaction_id) void openPaddle(value)
  else if (value.url) void navigateTo(value.url, { external: true })
  else {
    phase.value = 'test'
    open.value = true
  }
})

// ── The mock's test step (no Paddle) ─────────────────────────────────────────────────────────────────────────
const brand = ref<'visa' | 'mastercard' | 'amex' | 'discover'>('visa')
const brands = [
  { value: 'visa', label: 'Visa', icon: 'i-simple-icons-visa' },
  { value: 'mastercard', label: 'Mastercard', icon: 'i-simple-icons-mastercard' },
  { value: 'amex', label: 'American Express', icon: 'i-simple-icons-americanexpress' },
  { value: 'discover', label: 'Discover', icon: 'i-simple-icons-discover' },
]

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
  <AppModal v-model:open="open" :title="session?.purpose === 'add_card' ? t('billing.checkout.cardTitle') : t('billing.checkout.title')" :description="t('billing.checkout.desc')" :dismissible="phase !== 'confirming'" keep-open @after:leave="released">
    <template #body>
      <div v-if="session && phase === 'confirming'" class="flex flex-col items-center gap-3 py-6 text-center" role="status" aria-live="polite">
        <UIcon name="i-lucide-loader-circle" class="size-7 animate-spin text-muted" />
        <p class="text-sm font-medium text-highlighted">{{ t('billing.checkout.confirming') }}</p>
        <p class="max-w-sm text-xs text-muted">{{ t('billing.checkout.confirmingDesc') }}</p>
      </div>
      <div v-else-if="session" class="flex flex-col gap-4">
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
    <template v-if="phase === 'test'" #footer>
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
