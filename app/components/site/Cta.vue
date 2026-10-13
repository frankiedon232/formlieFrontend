<script setup lang="ts">
// The closing call to action on every page: a dark rounded panel (docs/DESIGN.md), with a line of light running
// through it.
const { t } = useI18n()
const localePath = useLocalePath()
const links = useSiteLinks()

const actions = computed(() => [
  {
    label: t('nav.startFree'),
    to: links.signup('starter'),
    size: 'xl' as const,
    color: 'neutral' as const,
    variant: 'solid' as const,
    class: 'bg-white text-neutral-950 hover:bg-white/90',
  },
  {
    label: t('home.hero.talkToSales'),
    to: `${localePath('/enterprise')}#enquiry`,
    size: 'xl' as const,
    color: 'neutral' as const,
    variant: 'outline' as const,
    class: 'bg-transparent text-white ring-white/30 hover:bg-white/10',
  },
])
</script>

<template>
  <UPageSection>
    <UPageCTA
      :title="t('home.cta.title')"
      :description="t('home.cta.description')"
      :links="actions"
      variant="naked"
      class="relative isolate overflow-hidden rounded-[1.5rem] bg-neutral-950"
      :ui="{ title: 'text-white', description: 'text-white/70' }"
    >
      <template #top>
        <div
          aria-hidden="true"
          class="absolute -start-24 -bottom-24 -z-10 size-80 rounded-full bg-violet-600/30 blur-3xl"
        />
        <svg
          aria-hidden="true"
          viewBox="0 0 800 200"
          preserveAspectRatio="none"
          class="absolute inset-0 -z-10 size-full opacity-60"
        >
          <path
            d="M -20 150 C 200 60, 420 220, 820 70"
            fill="none"
            stroke="white"
            stroke-opacity="0.12"
            stroke-width="1.2"
          />
          <path
            d="M -20 150 C 200 60, 420 220, 820 70"
            fill="none"
            stroke="#a78bfa"
            stroke-opacity="0.6"
            stroke-width="1.2"
            stroke-dasharray="2 10"
            class="motion-safe:animate-dash"
          />
        </svg>
      </template>
    </UPageCTA>
  </UPageSection>
</template>
