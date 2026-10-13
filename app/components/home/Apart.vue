<script setup lang="ts">
// "What sets Formalie apart": six cards with an ink icon tile (reference 1, docs/DESIGN.md "Feature card").
const { t } = useI18n()

const cards = computed(() =>
  (
    [
      ['data', 'i-lucide-database'],
      ['access', 'i-lucide-key-round'],
      ['channels', 'i-lucide-share-2'],
      ['languages', 'i-lucide-languages'],
      ['audit', 'i-lucide-scroll-text'],
      ['help', 'i-lucide-life-buoy'],
    ] as const
  ).map(([key, icon]) => ({ key, icon })),
)
</script>

<template>
  <UPageSection
    :headline="t('home.apart.eyebrow')"
    :title="t('home.apart.title')"
    :description="t('home.apart.description')"
  >
    <UPageGrid>
      <UPageCard
        v-for="card in cards"
        :key="card.key"
        :title="t(`home.apart.${card.key}.title`)"
        :description="t(`home.apart.${card.key}.text`)"
        variant="subtle"
        spotlight
        spotlight-color="neutral"
        class="group"
      >
        <template #leading>
          <span
            class="flex size-11 items-center justify-center rounded-xl bg-inverted text-inverted shadow-lg shadow-black/10 transition-transform motion-safe:group-hover:-translate-y-0.5 motion-safe:group-hover:rotate-3"
          >
            <UIcon :name="card.icon" class="size-5" />
          </span>
        </template>
      </UPageCard>
    </UPageGrid>
  </UPageSection>
</template>
