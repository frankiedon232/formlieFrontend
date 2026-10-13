<script setup lang="ts">
// Contact (docs/SITEMAP.md, docs/CONTENT.md): Sales (the Enterprise enquiry), Support (Formalie's own Contact
// support form FormalieHp, embedded below with an optional topic) and the help centre in the portal.
const route = useRoute()
const formKey = FORM_KEYS.support
const { t } = useI18n()
const localePath = useLocalePath()
const links = useSiteLinks()

const TOPICS = ['question', 'problem', 'billing', 'account', 'idea', 'other']
const prefill = computed(() => {
  const topic =
    typeof route.query.topic === 'string' && TOPICS.includes(route.query.topic)
      ? route.query.topic
      : undefined
  const subject =
    typeof route.query.subject === 'string' && route.query.subject.length <= 120
      ? route.query.subject
      : undefined
  return { topic, subject }
})

const cards = computed(() => [
  { key: 'sales', icon: 'i-lucide-briefcase', to: `${localePath('/enterprise')}#enquiry`, target: undefined },
  { key: 'support', icon: 'i-lucide-life-buoy', to: '#support', target: undefined },
  { key: 'help', icon: 'i-lucide-book-open', to: `${links.portal}/help`, target: '_blank' },
])

usePageSeo({
  title: () => t('nav.contact'),
  description: () => t('contactPage.metaDescription'),
  breadcrumbs: () => [{ name: t('nav.contact'), path: '/contact' }],
  schema: () => [
    {
      '@context': 'https://schema.org',
      '@type': 'ContactPage',
      name: t('contactPage.title'),
      description: t('contactPage.metaDescription'),
      mainEntity: {
        '@type': 'Organization',
        name: 'Formalie',
        contactPoint: [
          { '@type': 'ContactPoint', contactType: 'customer support', email: 'support@formalie.com' },
          { '@type': 'ContactPoint', contactType: 'sales', email: 'sales@formalie.com' },
        ],
      },
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
        :title="t('contactPage.title')"
        :description="t('contactPage.description')"
        :ui="{ title: 'text-balance', container: 'pb-6 sm:pb-8 lg:pb-8' }"
      >
        <template #headline>
          <UBadge
            :label="t('nav.contact')"
            icon="i-lucide-message-circle"
            color="neutral"
            variant="outline"
            size="lg"
            class="rounded-full px-3"
          />
        </template>
      </UPageHero>
    </div>

    <UContainer>
      <UPageGrid>
        <UPageCard
          v-for="card in cards"
          :key="card.key"
          :title="t(`contactPage.${card.key}.title`)"
          :description="t(`contactPage.${card.key}.text`)"
          :to="card.to"
          :target="card.target"
          variant="outline"
          class="group"
        >
          <template #leading>
            <span
              class="flex size-11 items-center justify-center rounded-xl bg-inverted text-inverted shadow-lg shadow-black/10 transition-transform motion-safe:group-hover:-translate-y-0.5"
            >
              <UIcon :name="card.icon" class="size-5" />
            </span>
          </template>
          <template #footer>
            <span class="flex items-center gap-1 text-sm font-medium text-highlighted">
              {{ t(`contactPage.${card.key}.button`) }}
              <UIcon
                :name="card.target ? 'i-lucide-arrow-up-right' : 'i-lucide-arrow-right'"
                class="size-4"
              />
            </span>
          </template>
        </UPageCard>
      </UPageGrid>
      <p class="mt-6 flex items-center justify-center gap-2 text-sm text-muted">
        <UIcon name="i-lucide-clock" class="size-4" />
        {{ t('contactPage.replies') }}
      </p>
    </UContainer>

    <UPageSection
      id="support"
      :title="t('contactPage.formTitle')"
      :description="t('contactPage.formDescription')"
      class="scroll-mt-16"
      :ui="{ container: 'lg:max-w-3xl' }"
    >
      <SiteFormEmbed :form-key="formKey" :name="t('contactPage.formTitle')" :prefill="prefill" />
    </UPageSection>
  </div>
</template>
