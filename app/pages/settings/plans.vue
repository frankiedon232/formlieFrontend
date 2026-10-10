<!--
  Settings → Plans (F24, owner 2026-10-10): the four plans side by side with a Monthly / Quarterly / Annually
  switch that changes every price (per month, the period's total and what it saves), the workspace's own plan
  marked, then every feature compared. Choosing a plan confirms the change (and pays through the processor
  when needed); Enterprise opens Formalie's enquiry form in the app's browser window.
-->
<script setup lang="ts">
import { BILLING_PERIODS, type PlanId } from '#shared/types/billing'
import { PERIOD_DISCOUNT } from '#shared/utils/billing/plans'

definePageMeta({ breadcrumb: 'settings.nav.plans' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.plans') })
const billing = useBilling()
const { overview, plans, failed, period } = billing
onMounted(() => billing.load())

const periods = computed(() => BILLING_PERIODS.map(value => ({ value, label: t(`billing.periodName.${value}`), off: PERIOD_DISCOUNT[value] })))
const sub = computed(() => overview.value?.subscription ?? null)
const choosing = ref<PlanId | null>(null)
const changeOpen = ref(false)
const { enquire } = useSupport()
function choose(plan: PlanId) {
  choosing.value = plan
  changeOpen.value = true
}
</script>

<template>
  <SettingsPage id="settings-plans" :title="t('settings.nav.plans')" :subtitle="t('settings.desc.plans')" icon="i-lucide-columns-3">
    <template #actions>
      <UButton :label="t('settings.nav.subscription')" icon="i-lucide-gem" color="neutral" variant="outline" to="/settings/subscription" />
    </template>
    <AppEmpty v-if="failed && !plans" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => billing.load() }]" />
    <div v-else-if="!plans || !overview" class="flex flex-col gap-6">
      <USkeleton class="mx-auto h-10 w-80 rounded-full" />
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4"><USkeleton v-for="n in 4" :key="n" class="h-96 rounded-xl" /></div>
    </div>
    <div v-else class="flex flex-col gap-8">
      <!-- The period switch: every price follows it -->
      <div class="flex flex-col items-center gap-2">
        <div class="inline-flex rounded-full bg-elevated p-1" role="radiogroup" :aria-label="t('billing.periodLabel')">
          <button
            v-for="item in periods"
            :key="item.value"
            type="button"
            role="radio"
            :aria-checked="period === item.value"
            class="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted) sm:px-4"
            :class="period === item.value ? 'bg-default font-medium text-highlighted shadow-sm' : 'text-muted hover:text-highlighted'"
            @click="period = item.value"
          >
            {{ item.label }}
            <span v-if="item.off" class="rounded-full bg-success/10 px-1.5 py-0.5 text-[10px] font-medium text-success">−{{ Math.round(item.off * 100) }}%</span>
          </button>
        </div>
        <p class="text-xs text-muted">{{ t('billing.pricesNote') }}</p>
      </div>

      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <BillingPlanCard
          v-for="plan in plans"
          :key="plan.id"
          :plan="plan"
          :period="period"
          :current="sub?.plan ?? null"
          :current-period="sub?.current_period_end ? sub.period : null"
          :scheduled="sub?.scheduled?.plan ?? (sub?.cancel_at_period_end ? 'starter' : null)"
          @choose="choose"
          @contact="enquire"
        />
      </div>

      <section class="flex flex-col gap-3">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('billing.compare.heading') }}</h2>
        <BillingCompare :plans="plans" :current="sub?.plan ?? null" />
      </section>

      <div class="flex flex-col items-start gap-3 rounded-xl border border-default bg-elevated/40 p-4 sm:flex-row sm:items-center">
        <UIcon name="i-lucide-building" class="size-6 shrink-0 text-highlighted" />
        <span class="flex min-w-0 flex-1 flex-col">
          <span class="text-sm font-semibold text-highlighted">{{ t('billing.enterpriseTitle') }}</span>
          <span class="text-xs text-muted">{{ t('billing.enterpriseDesc') }}</span>
        </span>
        <UButton :label="t('billing.contactUs')" icon="i-lucide-messages-square" color="neutral" @click="enquire" />
      </div>
    </div>

    <BillingChangeModal v-model:open="changeOpen" :plan="choosing" :period="choosing === 'starter' ? 'monthly' : period" />
    <BillingCheckoutModal />
  </SettingsPage>
</template>
