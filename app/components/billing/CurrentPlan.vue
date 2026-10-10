<!--
  The plan the workspace holds (F24): name, status, what it costs and when it renews or ends, any change waiting
  for the end of the period, and a past-due warning with its grace period. Change plan, cancel or keep it.
-->
<script setup lang="ts">
import type { BillingOverview } from '#shared/types/billing'

const props = defineProps<{ overview: BillingOverview }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { currency, date } = useFormat()
const confirm = useConfirm()
const billing = useBilling()

const sub = computed(() => props.overview.subscription)
const price = computed(() => props.overview.plan.prices?.[sub.value.period] ?? 0)
const STATUS_COLOR = { active: 'success', past_due: 'error', grace: 'warning', cancelled: 'neutral', expired: 'neutral' } as const
const statusKey = computed(() => (sub.value.cancel_at_period_end ? 'ending' : sub.value.status))

const { busy, run } = useBusy()
async function cancel() {
  if (!(await confirm({ title: t('billing.cancelTitle', { plan: t(`billing.plan.${sub.value.plan}.name`) }), description: t('billing.cancelDesc', { date: date(sub.value.current_period_end) }), confirmLabel: t('billing.cancelConfirm'), danger: true }))) return
  await run(async () => {
    billing.set((await api.post<BillingOverview>('/billing/cancel')).data)
    toast.add({ title: t('billing.cancelled', { date: date(sub.value.current_period_end) }), color: 'success', icon: 'i-lucide-calendar-x' })
  })
}
const resume = () => run(async () => {
  billing.set((await api.post<BillingOverview>('/billing/resume')).data)
  toast.add({ title: t('billing.resumed'), color: 'success', icon: 'i-lucide-rotate-ccw' })
})
const dropScheduled = () => run(async () => {
  billing.set((await api.del<BillingOverview>('/billing/scheduled')).data)
  toast.add({ title: t('billing.scheduleDropped'), color: 'success', icon: 'i-lucide-undo-2' })
})
</script>

<template>
  <div class="flex flex-col gap-4 rounded-xl border border-default p-4 sm:p-5">
    <div class="flex flex-wrap items-start gap-3">
      <span class="flex size-11 shrink-0 items-center justify-center rounded-xl bg-inverted text-inverted"><UIcon name="i-lucide-gem" class="size-5" /></span>
      <div class="flex min-w-0 flex-1 flex-col gap-1">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-lg font-semibold text-highlighted">{{ t(`billing.plan.${sub.plan}.name`) }}</span>
          <UBadge :label="t(`billing.status.${statusKey}`)" :color="sub.cancel_at_period_end ? 'warning' : STATUS_COLOR[sub.status]" variant="subtle" />
          <UBadge v-if="price" :label="t(`billing.periodName.${sub.period}`)" color="neutral" variant="outline" />
        </div>
        <p class="text-sm text-muted">
          <template v-if="!price">{{ t('billing.freeForever') }}</template>
          <template v-else-if="sub.cancel_at_period_end">{{ t('billing.endsOn', { date: date(sub.current_period_end) }) }}</template>
          <template v-else-if="sub.next_charge">{{ t('billing.renewsOn', { date: date(sub.next_charge.at), amount: currency(sub.next_charge.amount, sub.next_charge.currency) }) }}</template>
          <template v-else-if="sub.current_period_end">{{ t('billing.noRenewal', { date: date(sub.current_period_end) }) }}</template>
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <UButton :label="t('billing.changePlan')" icon="i-lucide-arrow-up-down" color="neutral" to="/settings/plans" />
        <UButton v-if="price && !sub.cancel_at_period_end" :label="t('billing.cancelPlan')" color="neutral" variant="outline" :loading="busy" @click="cancel" />
        <UButton v-if="sub.cancel_at_period_end" :label="t('billing.keepPlan')" icon="i-lucide-rotate-ccw" color="neutral" variant="outline" :loading="busy" @click="resume" />
      </div>
    </div>

    <UAlert v-if="sub.status === 'past_due'" color="error" variant="subtle" icon="i-lucide-circle-alert" :title="t('billing.pastDueTitle')" :description="t('billing.pastDueDesc', { date: date(sub.grace_until) })" :actions="[{ label: t('billing.addCard'), color: 'neutral', variant: 'outline', onClick: () => billing.addCard() }]" />
    <UAlert v-if="sub.status === 'expired'" color="neutral" variant="subtle" icon="i-lucide-info" :title="t('billing.expiredTitle')" :description="t('billing.expiredDesc')" />
    <UAlert
      v-if="sub.scheduled"
      color="neutral"
      variant="subtle"
      icon="i-lucide-calendar-clock"
      :title="t('billing.scheduledTitle', { plan: t(`billing.plan.${sub.scheduled.plan}.name`), period: t(`billing.periodName.${sub.scheduled.period}`), date: date(sub.scheduled.at) })"
      :actions="[{ label: t('billing.dropScheduled'), color: 'neutral', variant: 'outline', loading: busy, onClick: dropScheduled }]"
    />
    <UAlert v-if="price && sub.auto_renew && !sub.payment_method && !sub.cancel_at_period_end && sub.status === 'active'" color="warning" variant="subtle" icon="i-lucide-credit-card" :title="t('billing.noCardTitle')" :description="t('billing.noCardDesc', { date: date(sub.current_period_end) })" />
  </div>
</template>
