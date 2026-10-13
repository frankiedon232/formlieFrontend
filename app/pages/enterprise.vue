<script setup lang="ts">
// Enterprise (docs/SITEMAP.md, docs/CONTENT.md): what Enterprise adds, and the embedded Enterprise enquiry
// (Formalie's own form FormalieEn) at #enquiry, prefilled with what the visitor chose on the pricing page
// (plan, period, needs, residency, company, email from the address).
const route = useRoute()
const formKey = FORM_KEYS.enterprise
const { t, tm, rt } = useI18n()
const platform = usePlatform()

const ICONS = [
  'i-lucide-server',
  'i-lucide-globe',
  'i-lucide-key-round',
  'i-lucide-activity',
  'i-lucide-shield-check',
  'i-lucide-sliders-horizontal',
  'i-lucide-receipt',
  'i-lucide-graduation-cap',
]
const points = computed(() =>
  (tm('enterprisePage.points') as { title: unknown; text: unknown }[]).map((item, i) => ({
    title: rt(item.title as string),
    text: rt(item.text as string),
    icon: ICONS[i]!,
  })),
)

// Only the fields the enquiry accepts, and only short plain values (never anything else from the address).
const PREFILL = ['plan', 'period', 'needs', 'residency', 'company', 'email'] as const
const prefill = computed(() =>
  Object.fromEntries(
    PREFILL.map(key => {
      const value = route.query[key]
      return [key, typeof value === 'string' && value.length <= 120 ? value : undefined]
    }),
  ),
)

usePageSeo({
  title: () => t('enterprisePage.eyebrow'),
  fullTitle: () => `Formalie for ${t('enterprisePage.eyebrow')}`,
  description: () => t('enterprisePage.metaDescription'),
  breadcrumbs: () => [{ name: t('enterprisePage.eyebrow'), path: '/enterprise' }],
  schema: () => [
    {
      '@context': 'https://schema.org',
      '@type': 'Service',
      name: 'Formalie Enterprise',
      description: t('enterprisePage.metaDescription'),
      provider: { '@type': 'Organization', name: 'Formalie' },
      serviceType: points.value.map(point => point.title).join(', '),
    },
  ],
})
</script>

<template>
  <div>
    <div class="relative isolate overflow-hidden">
      <div aria-hidden="true" class="absolute inset-x-0 -top-40 -z-10 flex justify-center">
        <div class="h-[26rem] w-[50rem] rounded-full bg-violet-500/10 blur-3xl dark:bg-violet-500/15" />
      </div>
      <UPageHero
        orientation="horizontal"
        :title="t('enterprisePage.title')"
        :description="t('enterprisePage.description')"
        :links="[
          {
            label: t('home.hero.talkToSales'),
            to: '#enquiry',
            size: 'xl',
            color: 'neutral',
            trailingIcon: 'i-lucide-arrow-down',
          },
        ]"
        :ui="{ container: 'lg:grid-cols-[1fr_1fr] gap-12', title: 'text-balance' }"
      >
        <template #headline>
          <UBadge
            :label="t('enterprisePage.eyebrow')"
            icon="i-lucide-building-2"
            color="neutral"
            variant="outline"
            size="lg"
            class="rounded-full px-3"
          />
        </template>
        <EnterpriseVisual class="motion-safe:animate-rise" />
      </UPageHero>
    </div>

    <UPageSection>
      <UPageGrid class="lg:grid-cols-4">
        <UPageCard
          v-for="point in points"
          :key="point.title"
          :title="point.title"
          :description="point.text"
          variant="subtle"
        >
          <template #leading>
            <span
              class="flex size-11 items-center justify-center rounded-xl bg-inverted text-inverted shadow-lg shadow-black/10"
            >
              <UIcon :name="point.icon" class="size-5" />
            </span>
          </template>
        </UPageCard>
      </UPageGrid>
    </UPageSection>

    <UPageSection
      id="enquiry"
      :title="t('enterprisePage.formTitle')"
      :description="t('enterprisePage.formDescription')"
      class="scroll-mt-16"
      :ui="{ container: 'lg:max-w-3xl' }"
    >
      <SiteFormEmbed
        :form-key="formKey"
        :name="t('enterprisePage.formTitle')"
        :prefill="prefill"
        :email="platform.salesEmail"
      />
    </UPageSection>
  </div>
</template>
