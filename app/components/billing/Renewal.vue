<!--
  Automatic renewal and reminders (F24): renewal on or off (off: the plan ends with its period), reminders before
  renewal (7 and 1 days by default), when a payment fails and when the card is about to expire, to the owner and
  any extra addresses. Each change saves at once.
-->
<script setup lang="ts">
import type { BillingOverview, BillingReminders } from '#shared/types/billing'

const props = defineProps<{ overview: BillingOverview }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { date } = useFormat()
const confirm = useConfirm()
const billing = useBilling()

const sub = computed(() => props.overview.subscription)
const paid = computed(() => !!props.overview.plan.prices?.monthly)
const DAYS = [30, 14, 7, 3, 1] as const

const { busy, run } = useBusy()
async function save(change: { auto_renew?: boolean; reminders?: BillingReminders }) {
  await run(async () => {
    billing.set((await api.patch<BillingOverview>('/billing/settings', change)).data)
    toast.add({ title: t('billing.renewal.saved'), color: 'success', icon: 'i-lucide-check' })
  })
}
async function setRenew(value: boolean) {
  if (!value && paid.value && !(await confirm({ title: t('billing.renewal.offTitle'), description: t('billing.renewal.offDesc', { date: date(sub.value.current_period_end) }), confirmLabel: t('billing.renewal.offConfirm') }))) return
  await save({ auto_renew: value })
}
const reminders = computed(() => sub.value.reminders)
const toggleDay = (day: number) => save({ reminders: { ...reminders.value, before_renewal: reminders.value.before_renewal.includes(day) ? reminders.value.before_renewal.filter(item => item !== day) : [...reminders.value.before_renewal, day] } })
const emails = computed({
  get: () => reminders.value.extra_emails,
  set: list => save({ reminders: { ...reminders.value, extra_emails: [...new Set(list.map(item => item.trim().toLowerCase()).filter(item => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(item)))].slice(0, 5) } }),
})
</script>

<template>
  <div class="flex flex-col gap-4" :aria-busy="busy">
    <div class="flex items-center gap-3 rounded-lg border border-default p-3">
      <UIcon name="i-lucide-repeat" class="size-4 shrink-0 text-muted" />
      <span class="flex min-w-0 flex-1 flex-col">
        <span class="text-sm text-highlighted">{{ t('billing.renewal.auto') }}</span>
        <span class="text-xs text-muted">{{ !paid ? t('billing.renewal.freeHint') : sub.auto_renew ? t('billing.renewal.onHint', { date: date(sub.current_period_end) }) : t('billing.renewal.offHint', { date: date(sub.current_period_end) }) }}</span>
      </span>
      <USwitch :model-value="sub.auto_renew" color="neutral" :disabled="!paid || busy" :aria-label="t('billing.renewal.auto')" @update:model-value="setRenew" />
    </div>

    <div class="flex flex-col gap-3 rounded-lg border border-default p-3">
      <span class="flex items-center gap-2 text-sm text-highlighted"><UIcon name="i-lucide-bell-ring" class="size-4 text-muted" />{{ t('billing.renewal.reminders') }}</span>
      <div class="flex flex-col gap-1.5">
        <span class="text-xs text-muted">{{ t('billing.renewal.before') }}</span>
        <div class="flex flex-wrap gap-1.5" role="group" :aria-label="t('billing.renewal.before')">
          <UButton v-for="day in DAYS" :key="day" :label="t('billing.renewal.days', { n: day }, day)" color="neutral" :variant="reminders.before_renewal.includes(day) ? 'solid' : 'outline'" size="xs" class="rounded-full" :aria-pressed="reminders.before_renewal.includes(day)" :disabled="busy" @click="toggleDay(day)" />
        </div>
      </div>
      <div class="flex flex-col divide-y divide-default rounded-lg border border-default">
        <div class="flex items-center gap-3 px-3 py-2">
          <span class="flex-1 text-sm text-default">{{ t('billing.renewal.failed') }}</span>
          <USwitch :model-value="reminders.payment_failed" color="neutral" :disabled="busy" :aria-label="t('billing.renewal.failed')" @update:model-value="value => save({ reminders: { ...reminders, payment_failed: value } })" />
        </div>
        <div class="flex items-center gap-3 px-3 py-2">
          <span class="flex-1 text-sm text-default">{{ t('billing.renewal.expiring') }}</span>
          <USwitch :model-value="reminders.card_expiring" color="neutral" :disabled="busy" :aria-label="t('billing.renewal.expiring')" @update:model-value="value => save({ reminders: { ...reminders, card_expiring: value } })" />
        </div>
      </div>
      <UFormField :label="t('billing.renewal.alsoTo')" :help="t('billing.renewal.alsoToHelp')">
        <UInputTags v-model="emails" :placeholder="t('billing.renewal.emailPlaceholder')" icon="i-lucide-mail" class="w-full" :add-on-blur="true" :add-on-paste="true" :max="5" />
      </UFormField>
    </div>
  </div>
</template>
