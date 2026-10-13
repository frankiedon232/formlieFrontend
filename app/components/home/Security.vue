<script setup lang="ts">
// The dark security band: the controls on one side, a live audit trail on the other (entries slide in one by one).
const { t, tm, rt } = useI18n()
const localePath = useLocalePath()
const root = useTemplateRef<HTMLElement>('root')
const { paused } = useSectionMotion(root)

const points = computed(() => (tm('home.security.points') as unknown[]).map(point => rt(point as string)))

// Sample entries: international names, a neutral IP from the documentation range (RFC 5737).
const EVENTS = [
  { key: 'sso', who: 'Amara O.', icon: 'i-lucide-log-in', where: '203.0.113.24' },
  { key: 'published', who: 'Kenji S.', icon: 'i-lucide-send', where: '203.0.113.8' },
  { key: 'role', who: 'Lucía M.', icon: 'i-lucide-user-cog', where: '203.0.113.51' },
  { key: 'token', who: 'Omar H.', icon: 'i-lucide-key-round', where: '203.0.113.17' },
  { key: 'export', who: 'Priya N.', icon: 'i-lucide-download', where: '203.0.113.90' },
] as const
const FEED = 8 // seconds each entry stays (animate-feed)
</script>

<template>
  <section ref="root" class="px-4 py-8 sm:px-6 lg:px-8" :class="{ 'motion-paused': paused }">
    <div
      class="relative isolate mx-auto max-w-(--ui-container) overflow-hidden rounded-[1.5rem] bg-neutral-950 text-white"
    >
      <div
        aria-hidden="true"
        class="absolute inset-0 -z-10 opacity-60"
        style="
          background-image:
            linear-gradient(rgb(255 255 255 / 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgb(255 255 255 / 0.05) 1px, transparent 1px);
          background-size: 32px 32px;
          mask-image: linear-gradient(to bottom, black, transparent);
        "
      />
      <div
        aria-hidden="true"
        class="absolute -end-32 -top-32 -z-10 size-[28rem] rounded-full bg-violet-600/25 blur-3xl"
      />

      <div class="grid items-center gap-12 p-8 sm:p-12 lg:grid-cols-2 lg:p-16">
        <div>
          <p class="text-sm font-semibold text-violet-300">{{ t('home.security.eyebrow') }}</p>
          <h2 class="mt-3 text-3xl font-semibold tracking-tight text-pretty sm:text-4xl">
            {{ t('home.security.title') }}
          </h2>
          <p class="mt-4 text-white/70">{{ t('home.security.description') }}</p>
          <ul class="mt-8 space-y-3">
            <li v-for="point in points" :key="point" class="flex gap-3 text-sm text-white/85">
              <span
                class="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-white text-neutral-950"
              >
                <UIcon name="i-lucide-check" class="size-3" />
              </span>
              {{ point }}
            </li>
          </ul>
          <UButton
            :to="localePath('/security')"
            :label="t('home.security.link')"
            trailing-icon="i-lucide-arrow-right"
            color="neutral"
            variant="solid"
            size="lg"
            class="mt-8 bg-white text-neutral-950 hover:bg-white/90"
          />
        </div>

        <!-- A live audit trail (illustrative sample entries) -->
        <div
          aria-hidden="true"
          class="rounded-2xl bg-white/[0.04] p-4 ring-1 ring-white/10 backdrop-blur sm:p-6"
        >
          <div class="flex items-center justify-between border-b border-white/10 pb-3">
            <span class="flex items-center gap-2 text-sm font-medium">
              <UIcon name="i-lucide-scroll-text" class="size-4" />
              {{ t('home.security.trail') }}
            </span>
            <span class="flex items-center gap-1.5 text-xs text-emerald-300">
              <span class="relative flex size-2">
                <span
                  class="absolute inline-flex size-full rounded-full bg-emerald-400 motion-safe:animate-ping-soft"
                />
                <span class="relative inline-flex size-2 rounded-full bg-emerald-400" />
              </span>
              {{ t('home.security.live') }}
            </span>
          </div>
          <ul class="mt-3 space-y-2">
            <li
              v-for="(event, i) in EVENTS"
              :key="event.key"
              class="flex items-center gap-3 rounded-xl bg-white/[0.04] px-3 py-2.5 ring-1 ring-white/5 motion-safe:animate-feed motion-safe:[animation-fill-mode:backwards]"
              :style="{ animationDelay: `${(i * FEED) / EVENTS.length}s` }"
            >
              <span class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-white/10">
                <UIcon :name="event.icon" class="size-4" />
              </span>
              <span class="min-w-0 flex-1">
                <span class="block truncate text-sm font-medium">{{
                  t(`home.security.events.${event.key}`)
                }}</span>
                <span class="block truncate text-xs text-white/50" dir="ltr"
                  >{{ event.who }} · {{ event.where }}</span
                >
              </span>
              <UIcon name="i-lucide-shield-check" class="size-4 shrink-0 text-emerald-300" />
            </li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>
