<script setup lang="ts">
// Trust strip: sectors, not company logos, until the owner has real customers to show (CLAUDE.md rule 5).
const { t } = useI18n()

const sectors = computed(() =>
  (
    [
      ['hr', 'i-lucide-users'],
      ['healthcare', 'i-lucide-heart-pulse'],
      ['education', 'i-lucide-graduation-cap'],
      ['events', 'i-lucide-ticket'],
      ['finance', 'i-lucide-landmark'],
      ['operations', 'i-lucide-factory'],
    ] as const
  ).map(([key, icon]) => ({ key, icon, label: t(`home.trust.sectors.${key}`) })),
)
</script>

<template>
  <UContainer as="section" class="py-8 sm:py-10">
    <p class="text-center text-sm text-muted">{{ t('home.trust.title') }}</p>
    <ul class="mt-6 flex flex-wrap items-center justify-center gap-x-8 gap-y-4 sm:gap-x-12">
      <li
        v-for="sector in sectors"
        :key="sector.key"
        class="flex items-center gap-2 text-base font-semibold text-dimmed transition-colors hover:text-highlighted"
      >
        <UIcon :name="sector.icon" class="size-5" />
        {{ sector.label }}
      </li>
    </ul>
  </UContainer>
</template>
