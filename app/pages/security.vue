<script setup lang="ts">
// Security (docs/SITEMAP.md): the controls (never certifications Formalie doesn't hold, CLAUDE.md rule 5), the
// responsible disclosure contact, and links to the trust page and the legal documents.
const { t, tm, rt } = useI18n()
const localePath = useLocalePath()
const root = useTemplateRef<HTMLElement>('root')
const { still, paused } = useSectionMotion(root)

const ICONS = [
  'i-lucide-lock',
  'i-lucide-user-cog',
  'i-lucide-scroll-text',
  'i-lucide-smartphone',
  'i-lucide-globe',
  'i-lucide-hard-drive-download',
]
const items = computed(() =>
  (tm('securityPage.items') as { title: unknown; text: unknown }[]).map((item, i) => ({
    title: rt(item.title as string),
    text: rt(item.text as string),
    icon: ICONS[i]!,
  })),
)

const readMore = computed(() => [
  { label: t('securityPage.trust'), to: localePath('/trust'), icon: 'i-lucide-shield-check' },
  { label: t('legal.dataProtection'), to: localePath('/legal/data-protection'), icon: 'i-lucide-file-lock' },
  { label: t('legal.privacy'), to: localePath('/legal/privacy'), icon: 'i-lucide-eye-off' },
  { label: t('legal.subprocessors'), to: localePath('/legal/subprocessors'), icon: 'i-lucide-network' },
  { label: t('legal.acceptableUse'), to: localePath('/legal/acceptable-use'), icon: 'i-lucide-scale' },
])

usePageSeo({
  title: () => t('company.security'),
  description: () => t('securityPage.metaDescription'),
  breadcrumbs: () => [{ name: t('company.security'), path: '/security' }],
})
</script>

<template>
  <div>
    <!-- Dark hero with a shield the data passes through -->
    <section ref="root" class="px-4 pt-6 sm:px-6 lg:px-8" :class="{ 'motion-paused': paused }">
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
            mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
          "
        />
        <div
          aria-hidden="true"
          class="absolute start-1/2 top-1/2 -z-10 size-[30rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-violet-600/25 blur-3xl"
        />

        <div class="grid items-center gap-10 px-6 py-16 sm:px-12 lg:grid-cols-2 lg:px-16 lg:py-24">
          <div>
            <UBadge
              :label="t('company.security')"
              icon="i-lucide-shield-check"
              color="neutral"
              variant="subtle"
              size="lg"
              class="rounded-full bg-white/10 px-3 text-white ring-white/20"
            />
            <h1 class="mt-6 text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
              {{ t('securityPage.title') }}
            </h1>
            <p class="mt-4 text-lg text-white/70">{{ t('securityPage.description') }}</p>
          </div>

          <!-- Encrypted packets crossing a shield -->
          <div aria-hidden="true" class="relative mx-auto aspect-square w-full max-w-sm">
            <svg viewBox="0 0 300 300" class="absolute inset-0 size-full">
              <circle cx="150" cy="150" r="120" fill="none" stroke="white" stroke-opacity="0.08" />
              <circle
                cx="150"
                cy="150"
                r="90"
                fill="none"
                stroke="white"
                stroke-opacity="0.12"
                stroke-dasharray="3 6"
                class="motion-safe:animate-dash"
              />
              <path id="sec-line" d="M 0 150 L 300 150" fill="none" stroke="white" stroke-opacity="0.15" />
              <g v-if="!still">
                <!-- Hidden until its turn: before it starts, a packet would sit in the corner -->
                <rect v-for="i in 4" :key="i" width="22" height="10" rx="3" y="-5" fill="#a78bfa" opacity="0">
                  <set attributeName="opacity" to="0.9" :begin="`${(i - 1) * 1}s`" />
                  <animateMotion
                    path="M -20 150 L 320 150"
                    dur="4s"
                    :begin="`${(i - 1) * 1}s`"
                    repeatCount="indefinite"
                  />
                </rect>
              </g>
            </svg>
            <div
              class="absolute inset-[30%] flex items-center justify-center rounded-[28%] bg-white text-neutral-950 shadow-[0_0_60px_rgb(255_255_255/0.25)]"
            >
              <UIcon name="i-lucide-shield-check" class="size-1/2" />
            </div>
            <span
              class="absolute end-[18%] top-[18%] flex size-9 items-center justify-center rounded-full bg-white/10 ring-1 ring-white/20 backdrop-blur"
            >
              <UIcon name="i-lucide-lock" class="size-4" />
            </span>
            <span
              class="absolute start-[16%] bottom-[18%] flex size-9 items-center justify-center rounded-full bg-white/10 ring-1 ring-white/20 backdrop-blur"
            >
              <UIcon name="i-lucide-key-round" class="size-4" />
            </span>
          </div>
        </div>
      </div>
    </section>

    <UPageSection>
      <UPageGrid>
        <UPageCard
          v-for="item in items"
          :key="item.title"
          :title="item.title"
          :description="item.text"
          variant="subtle"
          spotlight
          spotlight-color="neutral"
        >
          <template #leading>
            <span
              class="flex size-11 items-center justify-center rounded-xl bg-inverted text-inverted shadow-lg shadow-black/10"
            >
              <UIcon :name="item.icon" class="size-5" />
            </span>
          </template>
        </UPageCard>
      </UPageGrid>
    </UPageSection>

    <UPageSection :ui="{ container: 'pt-0 sm:pt-0 lg:pt-0' }">
      <div class="grid gap-6 lg:grid-cols-2">
        <div class="rounded-3xl bg-inverted p-8 text-inverted sm:p-10">
          <UIcon name="i-lucide-bug" class="size-6" />
          <h2 class="mt-5 text-2xl font-semibold tracking-tight">{{ t('securityPage.disclosure.title') }}</h2>
          <i18n-t keypath="securityPage.disclosure.text" tag="p" class="mt-3 opacity-80" scope="global">
            <template #email>
              <a href="mailto:security@formalie.com" class="font-semibold underline underline-offset-4"
                >security@formalie.com</a
              >
            </template>
          </i18n-t>
          <UButton
            to="/.well-known/security.txt"
            external
            label="security.txt"
            icon="i-lucide-file-text"
            color="neutral"
            variant="outline"
            class="mt-6 bg-transparent text-inherit ring-current/30"
          />
        </div>
        <div class="rounded-3xl bg-default p-8 ring-1 ring-default sm:p-10">
          <h2 class="text-2xl font-semibold tracking-tight text-highlighted">
            {{ t('securityPage.linksTitle') }}
          </h2>
          <ul class="mt-5 divide-y divide-default">
            <li v-for="item in readMore" :key="item.to">
              <ULink :to="item.to" class="group flex items-center gap-3 py-3 text-highlighted">
                <UIcon :name="item.icon" class="size-5 text-muted" />
                <span class="flex-1 font-medium">{{ item.label }}</span>
                <UIcon
                  name="i-lucide-arrow-right"
                  class="size-4 text-muted transition-transform group-hover:translate-x-0.5 rtl:group-hover:-translate-x-0.5"
                />
              </ULink>
            </li>
          </ul>
        </div>
      </div>
    </UPageSection>

    <SiteCta />
  </div>
</template>
