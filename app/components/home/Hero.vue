<script setup lang="ts">
// Split hero after reference 1: headline, subline and two buttons on the start side, the data-flow panel on the
// end side (docs/DESIGN.md, docs/CONTENT.md).
const { t } = useI18n()
const localePath = useLocalePath()
const links = useSiteLinks()

const actions = computed(() => [
  {
    label: t('nav.startFree'),
    to: links.signup('starter'),
    size: 'xl' as const,
    color: 'neutral' as const,
    trailingIcon: 'i-lucide-arrow-right',
  },
  {
    label: t('home.hero.talkToSales'),
    to: `${localePath('/enterprise')}#enquiry`,
    size: 'xl' as const,
    color: 'neutral' as const,
    variant: 'outline' as const,
  },
])

const proof = computed(() => [
  { icon: 'i-lucide-badge-check', label: t('home.hero.proof.free') },
  { icon: 'i-lucide-languages', label: t('home.hero.proof.languages') },
  { icon: 'i-lucide-database', label: t('home.hero.proof.data') },
])
</script>

<template>
  <div class="relative isolate overflow-hidden">
    <!-- Soft background shapes (reference 2), one violet glow -->
    <div aria-hidden="true" class="absolute inset-x-0 -top-40 -z-10 flex justify-center">
      <div class="h-[28rem] w-[56rem] rounded-full bg-violet-500/10 blur-3xl dark:bg-violet-500/15" />
    </div>

    <UPageHero
      orientation="horizontal"
      :title="t('site.tagline')"
      :description="t('home.hero.description')"
      :links="actions"
      :ui="{
        container: 'lg:grid-cols-[1fr_1.15fr] gap-12 lg:gap-12',
        description: 'text-base sm:text-lg',
      }"
    >
      <template #headline>
        <UBadge
          :label="t('home.hero.eyebrow')"
          color="neutral"
          variant="outline"
          size="lg"
          class="rounded-full px-3 motion-safe:animate-rise"
          icon="i-lucide-sparkles"
        />
      </template>

      <template #footer>
        <ul class="mt-2 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted">
          <li v-for="item in proof" :key="item.label" class="flex items-center gap-1.5">
            <UIcon :name="item.icon" class="size-4 text-highlighted" />
            {{ item.label }}
          </li>
        </ul>
      </template>

      <FlowHero class="motion-safe:animate-rise [animation-delay:150ms]" />
    </UPageHero>
  </div>
</template>
