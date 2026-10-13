<script setup lang="ts">
import type { PricingPlanProps } from '@nuxt/ui'

// Pricing teaser: Starter, Professional (most popular) and Business from GET /public/plans (usePlans), monthly
// prices, then Enterprise. Samples are marked when the API doesn't answer.
const { t, locale } = useI18n()
const localePath = useLocalePath()
const links = useSiteLinks()
const { plans, source } = usePlans()

const cards = computed<PricingPlanProps[]>(() =>
  plans.value
    .filter(plan => plan.id !== 'enterprise' && plan.prices)
    .map(plan => {
      const monthly = plan.prices!.monthly
      const { limits } = plan
      const features = [
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
      const name = t(`home.pricing.plans.${plan.id}`)
      return {
        title: name,
        description: t(`home.pricing.taglines.${plan.id}`),
        price: monthly === 0 ? t('home.pricing.free') : formatPrice(monthly, plan.currency, locale.value),
        billingCycle: monthly === 0 ? undefined : `/ ${t('home.pricing.perMonth')}`,
        badge: plan.recommended ? t('home.pricing.mostPopular') : undefined,
        highlight: plan.recommended,
        scale: plan.recommended,
        features,
        button: {
          label: plan.id === 'starter' ? t('nav.startFree') : t('home.pricing.startWith', { plan: name }),
          to: links.signup(plan.id, 'monthly'),
          color: 'neutral' as const,
          variant: plan.recommended ? ('solid' as const) : ('outline' as const),
        },
      }
    }),
)
</script>

<template>
  <UPageSection
    :headline="t('home.pricing.eyebrow')"
    :title="t('home.pricing.title')"
    :description="t('home.pricing.description')"
  >
    <UPricingPlans :plans="cards" scale :ui="{ base: 'lg:grid-cols-3' }" />

    <div class="mt-10 flex flex-col items-center gap-4 text-center">
      <p class="text-sm text-muted">
        {{ t('home.pricing.enterprise') }}
        <ULink
          :to="`${localePath('/enterprise')}#enquiry`"
          class="font-medium text-highlighted underline-offset-4 hover:underline"
        >
          {{ t('home.hero.talkToSales') }}
        </ULink>
      </p>
      <div class="flex flex-wrap items-center justify-center gap-3">
        <UButton
          :to="localePath('/pricing')"
          :label="t('home.pricing.compare')"
          color="neutral"
          variant="ghost"
          trailing-icon="i-lucide-arrow-right"
        />
      </div>
      <p class="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-xs text-dimmed">
        <span class="flex items-center gap-1"
          ><UIcon name="i-lucide-shield-check" class="size-3.5" />{{ t('home.pricing.paddle') }}</span
        >
        <UBadge
          v-if="source === 'fallback'"
          :label="t('home.pricing.sample')"
          color="warning"
          variant="soft"
          size="sm"
        />
      </p>
    </div>
  </UPageSection>
</template>
