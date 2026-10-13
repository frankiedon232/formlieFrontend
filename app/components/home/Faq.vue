<script setup lang="ts">
import type { AccordionItem } from '@nuxt/ui'

// FAQ: one open at a time (docs/DESIGN.md), also given to search engines as FAQPage data.
const { t, tm, rt } = useI18n()

const items = computed<AccordionItem[]>(() =>
  (tm('home.faq.items') as { q: unknown; a: unknown }[]).map((item, i) => ({
    label: rt(item.q as string),
    content: rt(item.a as string),
    value: String(i),
  })),
)

useHead(() => ({
  script: [
    {
      key: 'faq-schema',
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: items.value.map(item => ({
          '@type': 'Question',
          name: item.label,
          acceptedAnswer: { '@type': 'Answer', text: item.content },
        })),
      }),
    },
  ],
}))
</script>

<template>
  <UPageSection :title="t('home.faq.title')" :ui="{ container: 'lg:max-w-3xl' }">
    <UAccordion
      :items="items"
      default-value="0"
      :ui="{ trigger: 'text-base font-semibold py-5', body: 'text-muted pb-5' }"
    />
  </UPageSection>
</template>
