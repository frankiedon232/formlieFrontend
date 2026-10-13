<script setup lang="ts">
import type { PricingPlanProps, TabsItem } from '@nuxt/ui'

// The period toggle and the four plan cards. Changing the period replays a soft rise on the cards, so the new
// prices arrive with a little movement (still for reduced motion).
const { t, tm, rt, locale } = useI18n()
const { plans, source, period, offer } = usePricing()

const periods = computed<TabsItem[]>(() =>
  PERIODS.map(value => {
    const saving = bestSaving(plans.value, value)
    return {
      value,
      label: t(`pricingPage.periods.${value}`),
      badge: saving
        ? {
            label: t('pricingPage.save', { percent: saving }),
            color: 'success' as const,
            variant: 'soft' as const,
            size: 'sm' as const,
          }
        : undefined,
    }
  }),
)

const ENTERPRISE_ICONS = [
  'i-lucide-globe',
  'i-lucide-users',
  'i-lucide-shield-check',
  'i-lucide-sliders-horizontal',
]

const cards = computed<PricingPlanProps[]>(() =>
  plans.value.map(plan => {
    const base = offer(plan)
    const { limits } = plan
    const features = plan.prices
      ? [
          limits.forms === null
            ? t('home.pricing.limits.formsUnlimited')
            : t('home.pricing.limits.forms', { count: limits.forms }),
          limits.responses_per_form === null
            ? t('home.pricing.limits.responsesUnlimited')
            : t('home.pricing.limits.responses', {
                count: new Intl.NumberFormat(locale.value).format(limits.responses_per_form),
              }),
          t('home.pricing.limits.databases', {
            list: limits.databases.map(engine => ENGINE_NAMES[engine]).join(', '),
          }),
          ...(limits.sso ? [t('home.pricing.limits.sso')] : []),
          t('home.pricing.limits.languages'),
        ]
      : (tm('pricingPage.enterpriseFeatures') as unknown[]).map((item, i) => ({
          title: rt(item as string),
          icon: ENTERPRISE_ICONS[i],
        }))
    return {
      ...base,
      features,
      scale: plan.recommended,
      variant: plan.id === 'enterprise' ? ('subtle' as const) : ('outline' as const),
    }
  }),
)
</script>

<template>
  <div>
    <div class="flex justify-center">
      <UTabs
        v-model="period"
        :items="periods"
        :content="false"
        color="neutral"
        variant="pill"
        size="lg"
        :aria-label="t('pricingPage.periodLabel')"
        :ui="{
          list: 'bg-elevated/60 ring-1 ring-default rounded-full',
          trigger: 'rounded-full px-3',
          trailingBadge: 'hidden sm:inline-flex',
          indicator: 'rounded-full',
        }"
      />
    </div>

    <div :key="period" class="mt-10 motion-safe:animate-rise">
      <UPricingPlans
        :plans="cards"
        scale
        :ui="{
          base: 'grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-2 lg:gap-x-6 xl:grid-cols-4 xl:gap-x-4',
        }"
      />
    </div>

    <div class="mt-8 flex flex-col items-center gap-2 text-center text-xs text-muted">
      <p class="flex items-center gap-1.5 font-medium text-toned">
        <UIcon name="i-lucide-shield-check" class="size-4" />
        {{ t('home.pricing.paddle') }}
      </p>
      <p>{{ t('pricingPage.taxNote') }}</p>
      <UAlert
        v-if="source === 'fallback'"
        :title="t('home.pricing.sample')"
        :description="t('pricingPage.sampleNote')"
        icon="i-lucide-info"
        color="warning"
        variant="soft"
        class="mt-2 max-w-md text-start"
      />
    </div>
  </div>
</template>
