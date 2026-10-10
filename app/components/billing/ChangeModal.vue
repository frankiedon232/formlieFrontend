<!--
  Confirming a plan change (F24): what changes and when (upgrades now, with the unused part of the current period
  taken off; downgrades and shorter periods at the end of the period), what is due now, and anything the
  workspace uses that the new plan doesn't allow. Paying with no card on file goes on to the checkout.
-->
<script setup lang="ts">
import type { BillingPeriod, DowngradeImpact, PlanId } from '#shared/types/billing'

const props = defineProps<{ plan: PlanId | null; period: BillingPeriod }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { currency, date } = useFormat()
const billing = useBilling()

interface Preview {
  plan: PlanId
  period: BillingPeriod
  price: number
  currency: string
  when: 'now' | 'period_end'
  starts_at: string
  credit: number
  due_now: number
  impact: DowngradeImpact
}
const preview = ref<Preview | null>(null)
/** One key per decision: confirming twice, or a retry after a dropped connection, is the same request. */
const requestKey = ref('')
watch(open, async value => {
  if (!value || !props.plan) return
  preview.value = null
  requestKey.value = crypto.randomUUID()
  try {
    preview.value = (await api.post<Preview>('/billing/preview', { plan: props.plan, period: props.period })).data
  } catch (error) {
    handle(error)
    open.value = false
  }
})

const { busy, run } = useBusy()
async function confirm() {
  if (!props.plan) return
  const done = await run(() => billing.change(props.plan!, props.period, requestKey.value))
  if (done === undefined) return
  open.value = false
  if (done) toast.add({ title: preview.value?.when === 'now' ? t('billing.changed', { plan: t(`billing.plan.${props.plan}.name`) }) : t('billing.changeScheduled', { plan: t(`billing.plan.${props.plan}.name`), date: date(preview.value!.starts_at) }), color: 'success', icon: 'i-lucide-circle-check' })
}
</script>

<template>
  <AppModal v-model:open="open" :title="plan ? t('billing.changeTitle', { plan: t(`billing.plan.${plan}.name`) }) : ''" :description="t('billing.changeDesc')">
    <template #body>
      <div v-if="!preview" class="flex flex-col gap-3"><USkeleton class="h-16 rounded-lg" /><USkeleton class="h-10 rounded-lg" /></div>
      <div v-else class="flex flex-col gap-4">
        <dl class="grid grid-cols-2 gap-3 rounded-lg border border-default p-3 text-sm">
          <div class="flex flex-col gap-0.5">
            <dt class="text-xs text-muted">{{ t('billing.starts') }}</dt>
            <dd class="text-highlighted">{{ preview.when === 'now' ? t('billing.startsNow') : t('billing.startsOn', { date: date(preview.starts_at) }) }}</dd>
          </div>
          <div class="flex flex-col gap-0.5">
            <dt class="text-xs text-muted">{{ t('billing.price') }}</dt>
            <dd class="text-highlighted tabular-nums">{{ preview.price ? t(`billing.pricePer.${preview.period}`, { amount: currency(preview.price, preview.currency) }) : t('billing.free') }}</dd>
          </div>
          <div v-if="preview.credit" class="flex flex-col gap-0.5">
            <dt class="text-xs text-muted">{{ t('billing.credit') }}</dt>
            <dd class="text-success tabular-nums">−{{ currency(preview.credit, preview.currency) }}</dd>
          </div>
          <div class="flex flex-col gap-0.5">
            <dt class="text-xs text-muted">{{ t('billing.dueNow') }}</dt>
            <dd class="font-semibold text-highlighted tabular-nums">{{ currency(preview.due_now, preview.currency) }}</dd>
          </div>
        </dl>
        <p class="text-xs text-muted">{{ preview.when === 'now' ? t('billing.nowNote') : plan === 'starter' ? t('billing.cancelNote') : t('billing.laterNote') }}</p>
        <UAlert
          v-if="preview.impact.over.length"
          color="warning"
          variant="subtle"
          icon="i-lucide-triangle-alert"
          :title="t('billing.overTitle')"
        >
          <template #description>
            <ul class="flex list-disc flex-col gap-1 ps-4">
              <li v-for="item in preview.impact.over" :key="item.key">{{ t(`billing.over.${item.key}`, { current: item.current, allowed: item.allowed }) }}</li>
            </ul>
            <p class="mt-2">{{ t('billing.overNote') }}</p>
          </template>
        </UAlert>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="ghost" :disabled="busy" @click="open = false" />
        <UButton :label="preview?.due_now && !billing.overview.value?.subscription.payment_method ? t('billing.continuePay') : t('billing.confirmChange')" icon="i-lucide-check" color="neutral" :loading="busy" :disabled="!preview" @click="confirm" />
      </div>
    </template>
  </AppModal>
</template>
