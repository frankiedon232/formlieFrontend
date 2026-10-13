<script setup lang="ts">
import type { PricingTableSection, PricingTableTier } from '@nuxt/ui'

// The full comparison (docs/PRICING.md), grouped like the app's Settings → Plans, from what each plan includes
// (app/utils/pricing.ts). The header follows the chosen period.
const { t, locale } = useI18n()
const { plans, offer } = usePricing()

const tiers = computed<PricingTableTier[]>(() =>
  plans.value.map(plan => {
    // The table header stays compact: name, price and the button, "/ month" for paid plans.
    const { title, price, discount, button, highlight } = offer(plan)
    const paid = !!plan.prices && plan.prices.monthly > 0
    return {
      id: plan.id,
      title,
      price,
      discount,
      button,
      highlight,
      billingCycle: paid ? t('pricingPage.perMonth') : undefined,
    }
  }),
)

const cell = (value: Cell): boolean | string => {
  if (typeof value === 'boolean') return value
  if (value === 'unlimited') return t('pricingPage.compare.unlimited')
  if (value === 'custom') return t('pricingPage.custom')
  return new Intl.NumberFormat(locale.value).format(value)
}

const sections = computed<PricingTableSection[]>(() =>
  comparison(plans.value).map(group => ({
    id: group.key,
    title: t(`pricingPage.compare.groups.${group.key}`),
    features: group.rows.map(row => ({
      id: row.engine ? `${row.key}-${row.engine}` : row.key,
      title: row.engine
        ? t('pricingPage.compare.rows.database', { engine: ENGINE_NAMES[row.engine] })
        : t(`pricingPage.compare.rows.${row.key}`),
      tiers: Object.fromEntries(Object.entries(row.cells).map(([id, value]) => [id, cell(value as Cell)])),
    })),
  })),
)
</script>

<template>
  <UPageSection
    id="compare"
    :title="t('pricingPage.compare.title')"
    :description="t('pricingPage.compare.description')"
    class="scroll-mt-16"
  >
    <UPricingTable
      :tiers="tiers"
      :sections="sections"
      :caption="t('pricingPage.compare.title')"
      :ui="{ tier: 'rounded-t-2xl', featureTitle: 'text-sm' }"
    />
  </UPageSection>
</template>
