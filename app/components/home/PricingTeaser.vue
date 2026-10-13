<script setup lang="ts">
// Pricing on the home page: exactly the pricing page's plans (owner, 2026-10-13: the same four plans, the same
// period switch and prices), from GET /public/plans through PricingPlans, then a link to the full comparison.
const { t } = useI18n()
const localePath = useLocalePath()
</script>

<template>
  <UPageSection
    :headline="t('home.pricing.eyebrow')"
    :title="t('home.pricing.title')"
    :description="t('home.pricing.description')"
  >
    <PricingPlans />

    <div class="mt-6 flex justify-center">
      <UButton
        :to="localePath('/pricing')"
        :label="t('home.pricing.compare')"
        color="neutral"
        variant="outline"
        trailing-icon="i-lucide-arrow-right"
      />
    </div>
  </UPageSection>
</template>
