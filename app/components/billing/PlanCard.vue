<!--
  One plan on the Plans page (F24): name and who it is for, the price for the chosen period (per month, with the
  period's total and saving), the key limits, and one button: current plan, upgrade, downgrade, or contact us.
  All cards share the same structure so the rows line up.
-->
<script setup lang="ts">
import type { BillingPeriod, Plan, PlanId } from '#shared/types/billing'
import { monthlyEquivalent, periodSaving, planRank } from '#shared/utils/billing/plans'

const props = defineProps<{ plan: Plan; period: BillingPeriod; current: PlanId | null; currentPeriod: BillingPeriod | null; scheduled?: PlanId | null; busy?: boolean }>()
const emit = defineEmits<{ choose: [plan: PlanId]; contact: [] }>()
const { t } = useI18n()
const { currency, number } = useFormat()

const isCurrent = computed(() => props.current === props.plan.id && (props.plan.id === 'starter' || props.currentPeriod === props.period))
const free = computed(() => props.plan.prices?.monthly === 0)
const perMonth = computed(() => monthlyEquivalent(props.plan, props.period))
const saving = computed(() => periodSaving(props.plan, props.period))
const action = computed(() => {
  if (!props.plan.prices) return { label: t('billing.contactUs'), icon: 'i-lucide-messages-square', variant: 'outline' as const }
  if (isCurrent.value) return { label: t('billing.currentPlan'), icon: 'i-lucide-check', variant: 'soft' as const }
  if (props.scheduled === props.plan.id) return { label: t('billing.scheduledShort'), icon: 'i-lucide-calendar-clock', variant: 'soft' as const }
  const up = props.current === null || planRank(props.plan.id) > planRank(props.current) || (props.plan.id === props.current && props.period !== props.currentPeriod)
  return up ? { label: props.plan.id === props.current ? t('billing.switchPeriod') : t('billing.upgrade'), icon: 'i-lucide-arrow-up-right', variant: 'solid' as const } : { label: t('billing.downgrade'), icon: 'i-lucide-arrow-down-right', variant: 'outline' as const }
})

const limit = (value: number | null) => (value === null ? t('billing.unlimited') : number(value))
const facts = computed(() => {
  const l = props.plan.limits
  return [
    { icon: 'i-lucide-file-text', text: l.forms === null ? t('billing.fact.formsUnlimited') : t('billing.fact.forms', { n: number(l.forms) }, l.forms) },
    { icon: 'i-lucide-inbox', text: l.responses_per_form === null ? t('billing.fact.responsesUnlimited') : t('billing.fact.responses', { n: limit(l.responses_per_form) }) },
    { icon: 'i-lucide-database', text: l.databases.length === 5 ? t('billing.fact.databasesAll') : t('billing.fact.databases', { list: l.databases.map(engine => t(`billing.db.${engine}`)).join(', ') }) },
    { icon: 'i-lucide-log-in', text: l.sso ? t('billing.fact.signinAll') : t('billing.fact.signinEmail') },
    { icon: 'i-lucide-globe', text: l.custom_domains === 0 ? t('billing.fact.subdomain') : l.custom_domains === null ? t('billing.fact.domains') : t('billing.fact.domain') },
    { icon: 'i-lucide-mail-check', text: l.custom_email ? t('billing.fact.email') : t('billing.fact.emailFormalie') },
    { icon: 'i-lucide-sparkles', text: l.ai_credits === null ? t('billing.fact.aiCustom') : t('billing.fact.ai', { n: number(l.ai_credits) }) },
  ]
})
</script>

<template>
  <article class="flex h-full flex-col gap-4 rounded-xl border p-4 sm:p-5" :class="plan.recommended ? 'border-inverted shadow-md' : 'border-default'">
    <header class="flex flex-col gap-1">
      <div class="flex items-center gap-2">
        <h3 class="text-base font-semibold text-highlighted">{{ t(`billing.plan.${plan.id}.name`) }}</h3>
        <UBadge v-if="plan.recommended" :label="t('billing.popular')" color="neutral" variant="solid" size="sm" />
        <UBadge v-if="isCurrent" :label="t('billing.yours')" color="success" variant="subtle" size="sm" class="ms-auto" />
      </div>
      <p class="min-h-10 text-xs text-muted">{{ t(`billing.plan.${plan.id}.bestFor`) }}</p>
    </header>

    <div class="flex min-h-20 flex-col gap-0.5">
      <template v-if="!plan.prices">
        <span class="text-2xl font-semibold text-highlighted">{{ t('billing.custom') }}</span>
        <span class="text-xs text-muted">{{ t('billing.customHint') }}</span>
      </template>
      <template v-else-if="free">
        <span class="text-2xl font-semibold text-highlighted">{{ t('billing.free') }}</span>
        <span class="text-xs text-muted">{{ t('billing.freeHint') }}</span>
      </template>
      <template v-else>
        <span class="flex items-baseline gap-1"><span class="text-2xl font-semibold text-highlighted tabular-nums">{{ currency(perMonth, plan.currency) }}</span><span class="text-xs text-muted">{{ t('billing.perMonth') }}</span></span>
        <span class="text-xs text-muted">{{ period === 'monthly' ? t('billing.billedMonthly') : t(`billing.billed.${period}`, { total: currency(plan.prices[period], plan.currency) }) }}</span>
        <UBadge v-if="saving > 0" :label="t('billing.save', { amount: currency(saving, plan.currency) })" color="success" variant="subtle" size="sm" class="mt-1 self-start" />
      </template>
    </div>

    <UButton
      :label="action.label"
      :icon="action.icon"
      color="neutral"
      :variant="action.variant"
      block
      :loading="busy"
      :disabled="isCurrent || scheduled === plan.id"
      @click="plan.prices ? emit('choose', plan.id) : emit('contact')"
    />

    <ul class="flex flex-col gap-2 border-t border-default pt-4 text-sm">
      <li v-for="fact in facts" :key="fact.icon" class="flex items-start gap-2">
        <UIcon :name="fact.icon" class="mt-0.5 size-4 shrink-0 text-muted" />
        <span class="text-default">{{ fact.text }}</span>
      </li>
    </ul>
    <p class="mt-auto text-xs text-muted">{{ t(`billing.plan.${plan.id}.everything`) }}</p>
  </article>
</template>
