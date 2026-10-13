<script setup lang="ts">
// "Built for teams in every sector": sectors, not company logos, until the owner has real customers to show
// (CLAUDE.md rule 5). Two rows glide in opposite directions (UMarquee, still for reduced motion); each card has a
// small live pulse, like answers arriving.
const { t } = useI18n()

const SECTORS = [
  ['hr', 'i-lucide-users'],
  ['healthcare', 'i-lucide-heart-pulse'],
  ['education', 'i-lucide-graduation-cap'],
  ['events', 'i-lucide-ticket'],
  ['finance', 'i-lucide-landmark'],
  ['operations', 'i-lucide-settings-2'],
  ['government', 'i-lucide-building-2'],
  ['nonprofit', 'i-lucide-hand-heart'],
  ['retail', 'i-lucide-shopping-bag'],
  ['hospitality', 'i-lucide-concierge-bell'],
  ['construction', 'i-lucide-hard-hat'],
  ['logistics', 'i-lucide-truck'],
  ['legal', 'i-lucide-scale'],
  ['realEstate', 'i-lucide-house'],
  ['manufacturing', 'i-lucide-factory'],
  ['technology', 'i-lucide-cpu'],
  ['research', 'i-lucide-flask-conical'],
  ['insurance', 'i-lucide-shield-check'],
] as const

const sectors = computed(() =>
  SECTORS.map(([key, icon], i) => ({
    key,
    icon,
    label: t(`home.trust.sectors.${key}`),
    delay: (i % 6) * 0.4,
  })),
)
const rows = computed(() => [sectors.value.slice(0, 9), sectors.value.slice(9)])
</script>

<template>
  <section class="relative isolate overflow-hidden border-y border-default bg-elevated/30 py-10 sm:py-12">
    <div
      aria-hidden="true"
      class="absolute inset-x-0 top-1/2 -z-10 mx-auto h-40 max-w-3xl -translate-y-1/2 rounded-full bg-violet-500/5 blur-3xl"
    />

    <UContainer class="text-center">
      <h2 class="text-base font-semibold text-highlighted sm:text-lg">{{ t('home.trust.title') }}</h2>
      <p class="mx-auto mt-1 max-w-2xl text-sm text-muted">{{ t('home.trust.description') }}</p>
    </UContainer>

    <div class="mt-7 flex flex-col gap-3">
      <UMarquee
        v-for="(row, r) in rows"
        :key="r"
        :reverse="r === 1"
        pause-on-hover
        :overlay="true"
        :ui="{ root: '[--duration:45s] [--gap:--spacing(3)]' }"
      >
        <span
          v-for="sector in row"
          :key="sector.key"
          class="group flex items-center gap-2.5 rounded-2xl bg-default py-2 ps-2 pe-4 text-sm font-medium whitespace-nowrap text-highlighted shadow-sm ring-1 ring-default transition-shadow hover:shadow-md"
        >
          <span class="flex size-8 items-center justify-center rounded-xl bg-inverted text-inverted">
            <UIcon :name="sector.icon" class="size-4" />
          </span>
          {{ sector.label }}
          <span aria-hidden="true" class="relative ms-1 flex size-2">
            <span
              class="absolute inline-flex size-full rounded-full bg-emerald-500 motion-safe:animate-ping-soft"
              :style="{ animationDelay: `${sector.delay}s` }"
            />
            <span class="relative inline-flex size-2 rounded-full bg-emerald-500" />
          </span>
        </span>
      </UMarquee>
    </div>
  </section>
</template>
