<!--
  A plan-only part of a page the workspace's plan doesn't include (F24 M3): which plan brings it and a way to
  the plans (admins). `inline` is the small badge beside a switch; otherwise a short notice.
-->
<script setup lang="ts">
const props = defineProps<{ feature: PlanFeatureKey; inline?: boolean }>()
const { t } = useI18n()
const { minimumFor } = usePlanAccess()
const { can } = useCan()
const planName = computed(() => t(`billing.plan.${minimumFor(props.feature)}.name`))
</script>

<template>
  <UTooltip v-if="inline" :text="t('billing.lockedHint')">
    <UBadge :label="t('billing.locked', { plan: planName })" icon="i-lucide-gem" color="neutral" variant="outline" size="sm" class="shrink-0" />
  </UTooltip>
  <div v-else class="flex flex-wrap items-center gap-3 rounded-lg border border-dashed border-accented bg-elevated/40 p-3">
    <UIcon name="i-lucide-gem" class="size-4 shrink-0 text-highlighted" />
    <span class="flex min-w-0 flex-1 flex-col">
      <span class="text-sm font-medium text-highlighted">{{ t('billing.locked', { plan: planName }) }}</span>
      <span class="text-xs text-muted">{{ can('settings.manage') ? t('billing.lockedHint') : t('billing.limitMember') }}</span>
    </span>
    <UButton v-if="can('settings.manage')" :label="t('billing.seePlans')" icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="sm" to="/settings/plans" />
  </div>
</template>
