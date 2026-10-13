<script setup lang="ts">
import type { AccordionItem } from '@nuxt/ui'

// Pricing (docs/SITEMAP.md, docs/PRICING.md): the period toggle, four plans from GET /public/plans, the full
// comparison, the pricing FAQ and the call to action. Structured data: SoftwareApplication with one Offer per plan
// and period, FAQPage and breadcrumbs (docs/SEO.md).
const { t, tm, rt } = useI18n()
const localePath = useLocalePath()
const links = useSiteLinks()
const { plans } = usePricing()

const faq = computed<AccordionItem[]>(() =>
  (tm('pricingPage.faq.items') as { q: unknown; a: unknown }[]).map((item, i) => ({
    label: rt(item.q as string),
    content: rt(item.a as string),
    value: String(i),
  })),
)

const offers = computed(() =>
  plans.value.flatMap(plan =>
    plan.prices
      ? PERIODS.map(period => ({
          '@type': 'Offer',
          name: `Formalie ${t(`home.pricing.plans.${plan.id}`)}, ${t(`pricingPage.periods.${period}`)}`,
          price: plan.prices![period],
          priceCurrency: plan.currency,
          url: `${links.site}${localePath('/pricing')}`,
          availability: 'https://schema.org/InStock',
          priceSpecification: {
            '@type': 'UnitPriceSpecification',
            price: plan.prices![period],
            priceCurrency: plan.currency,
            billingDuration: PERIOD_MONTHS[period],
            unitCode: 'MON',
          },
        }))
      : [],
  ),
)

usePageSeo({
  title: () => t('nav.pricing'),
  description: () => t('pricingPage.metaDescription'),
  imageAlt: () => t('pricingPage.title'),
  breadcrumbs: () => [{ name: t('nav.pricing'), path: '/pricing' }],
  schema: () => [
    {
      '@context': 'https://schema.org',
      '@type': 'SoftwareApplication',
      name: 'Formalie',
      applicationCategory: 'BusinessApplication',
      operatingSystem: 'Web',
      url: links.site,
      offers: offers.value,
    },
    {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: faq.value.map(item => ({
        '@type': 'Question',
        name: item.label,
        acceptedAnswer: { '@type': 'Answer', text: item.content },
      })),
    },
  ],
})
</script>

<template>
  <div>
    <div class="relative isolate overflow-hidden">
      <div aria-hidden="true" class="absolute inset-x-0 -top-40 -z-10 flex justify-center">
        <div class="h-[26rem] w-[56rem] rounded-full bg-violet-500/10 blur-3xl dark:bg-violet-500/15" />
      </div>
      <UPageHero
        :title="t('pricingPage.title')"
        :description="t('pricingPage.description')"
        :ui="{ title: 'text-balance', container: 'pb-6 sm:pb-8 lg:pb-8' }"
      >
        <template #headline>
          <UBadge
            :label="t('pricingPage.eyebrow')"
            icon="i-lucide-tag"
            color="neutral"
            variant="outline"
            size="lg"
            class="rounded-full px-3"
          />
        </template>
      </UPageHero>
    </div>

    <UContainer class="pb-12 sm:pb-16">
      <PricingPlans />
      <div class="mt-6 flex justify-center">
        <UButton
          to="#compare"
          :label="t('pricingPage.compare.title')"
          color="neutral"
          variant="ghost"
          trailing-icon="i-lucide-arrow-down"
        />
      </div>
    </UContainer>

    <PricingCompare />

    <UPageSection :title="t('pricingPage.faq.title')" :ui="{ container: 'lg:max-w-3xl' }">
      <UAccordion
        :items="faq"
        default-value="0"
        :ui="{ trigger: 'text-base font-semibold py-5', body: 'text-muted pb-5' }"
      />
      <p class="mt-6 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted">
        {{ t('pricingPage.faq.more') }}:
        <ULink
          :to="localePath('/legal/refunds')"
          class="font-medium text-highlighted underline-offset-4 hover:underline"
        >
          {{ t('legal.refunds') }}
        </ULink>
        <ULink
          :to="localePath('/legal/terms')"
          class="font-medium text-highlighted underline-offset-4 hover:underline"
        >
          {{ t('legal.terms') }}
        </ULink>
      </p>
    </UPageSection>

    <LazySiteCta hydrate-on-visible />
  </div>
</template>
