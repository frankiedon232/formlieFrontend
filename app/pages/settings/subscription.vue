<!--
  Settings → Subscription (F24, owner 2026-10-10): the plan the workspace holds (always active: new workspaces
  are on Starter), usage against its limits, the card renewals are charged to (add through the processor,
  remove), automatic renewal and reminders (on by default), and invoices. Changing plan opens Plans.
-->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'settings.nav.subscription' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.subscription') })
const billing = useBilling()
const { overview, failed } = billing
onMounted(() => billing.load({ invoices: true }))
// After a checkout or a change, the invoices list is refreshed
watch(billing.invoices, list => list === null && overview.value && void billing.load({ invoices: true }))
</script>

<template>
  <SettingsPage id="settings-subscription" :title="t('settings.nav.subscription')" :subtitle="t('settings.desc.subscription')" icon="i-lucide-gem">
    <template #actions>
      <UButton :label="t('billing.comparePlans')" icon="i-lucide-columns-3" color="neutral" variant="outline" to="/settings/plans" />
    </template>
    <AppEmpty v-if="failed && !overview" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => billing.load({ invoices: true }) }]" />
    <div v-else-if="!overview" class="flex flex-col gap-6"><USkeleton class="h-28 rounded-xl" /><USkeleton v-for="n in 3" :key="n" class="h-36 rounded-lg" /></div>
    <div v-else class="flex flex-col gap-6">
      <BillingCurrentPlan :overview="overview" />
      <SettingsBlock :title="t('billing.block.usage')" :description="t('billing.block.usageHint')" icon="i-lucide-gauge">
        <BillingUsage :overview="overview" />
      </SettingsBlock>
      <SettingsBlock :title="t('billing.block.payment')" :description="t('billing.block.paymentHint')" icon="i-lucide-credit-card">
        <BillingPaymentMethod :overview="overview" />
      </SettingsBlock>
      <SettingsBlock :title="t('billing.block.renewal')" :description="t('billing.block.renewalHint')" icon="i-lucide-repeat">
        <BillingRenewal :overview="overview" />
      </SettingsBlock>
      <SettingsBlock :title="t('billing.block.invoices')" :description="t('billing.block.invoicesHint')" icon="i-lucide-receipt-text">
        <BillingInvoices :invoices="billing.invoices.value" />
      </SettingsBlock>
    </div>
    <BillingCheckoutModal />
  </SettingsPage>
</template>
