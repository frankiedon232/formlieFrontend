<script setup lang="ts">
// Trust and security (formlyBackend docs/legal/trust-and-security.md, owner 2026-10-13): the controls Formalie has
// today, your rights and our commitments, and how to report a problem. The "Independent checks (when ready)"
// section stays out until the owner adds it. Controls only, never certifications (CLAUDE.md rule 5).
const { t, tm, rt } = useI18n()
const localePath = useLocalePath()
const root = useTemplateRef<HTMLElement>('root')
const { paused } = useSectionMotion(root)

const ICONS = [
  'i-lucide-boxes',
  'i-lucide-lock',
  'i-lucide-user-cog',
  'i-lucide-scroll-text',
  'i-lucide-key-round',
  'i-lucide-database',
  'i-lucide-hard-drive-download',
  'i-lucide-shield-alert',
  'i-lucide-credit-card',
  'i-lucide-eye-off',
]
const items = computed(() =>
  (tm('trustPage.items') as { title: unknown; text: unknown }[]).map((item, i) => ({
    title: rt(item.title as string),
    text: rt(item.text as string),
    icon: ICONS[i]!,
  })),
)

const rights = computed(() =>
  (['privacy', 'data-protection', 'subprocessors', 'cookies'] as const).map(slug => ({
    label: t(`legal.${LEGAL_KEYS[slug]}`),
    to: localePath(`/legal/${slug}`),
  })),
)

usePageSeo({
  title: () => t('trustPage.title'),
  description: () => t('trustPage.metaDescription'),
  breadcrumbs: () => [{ name: t('trustPage.title'), path: '/trust' }],
})
</script>

<template>
  <div>
    <div class="relative isolate overflow-hidden">
      <div aria-hidden="true" class="absolute inset-x-0 -top-40 -z-10 flex justify-center">
        <div class="h-[26rem] w-[50rem] rounded-full bg-violet-500/10 blur-3xl dark:bg-violet-500/15" />
      </div>
      <UPageHero
        :title="t('trustPage.title')"
        :description="t('trustPage.description')"
        :ui="{ title: 'text-balance' }"
      >
        <template #headline>
          <!-- A shield with rings slowly turning: protection that is always on -->
          <div
            ref="root"
            aria-hidden="true"
            class="relative mx-auto size-20"
            :class="{ 'motion-paused': paused }"
          >
            <span
              class="absolute inset-0 rounded-full border border-dashed border-accented motion-safe:animate-orbit"
            />
            <span
              class="absolute inset-2 rounded-full border border-default motion-safe:animate-orbit-reverse"
            />
            <span
              class="absolute inset-5 flex items-center justify-center rounded-2xl bg-inverted text-inverted shadow-lg shadow-black/10"
            >
              <UIcon name="i-lucide-shield-check" class="size-5" />
            </span>
          </div>
        </template>
      </UPageHero>
    </div>

    <UPageSection :title="t('trustPage.protectTitle')">
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
        <div class="rounded-3xl bg-default p-8 ring-1 ring-default sm:p-10">
          <h2 class="text-2xl font-semibold tracking-tight text-highlighted">
            {{ t('trustPage.rightsTitle') }}
          </h2>
          <ul class="mt-5 divide-y divide-default">
            <li v-for="item in rights" :key="item.to">
              <ULink :to="item.to" class="group flex items-center gap-3 py-3 font-medium text-highlighted">
                <UIcon name="i-lucide-file-text" class="size-5 text-muted" />
                <span class="flex-1">{{ item.label }}</span>
                <UIcon name="i-lucide-arrow-right" class="size-4 text-muted" />
              </ULink>
            </li>
          </ul>
          <p class="mt-5 text-sm text-muted">{{ t('trustPage.laws') }}</p>
        </div>

        <div class="rounded-3xl bg-inverted p-8 text-inverted sm:p-10">
          <h2 class="text-2xl font-semibold tracking-tight">{{ t('trustPage.reportTitle') }}</h2>
          <ul class="mt-5 space-y-4 text-sm opacity-90">
            <li class="flex gap-3">
              <UIcon name="i-lucide-bug" class="mt-0.5 size-5 shrink-0" />
              <i18n-t keypath="trustPage.reportSecurity" tag="span" scope="global">
                <template #email>
                  <a href="mailto:security@formalie.com" class="font-semibold underline underline-offset-4"
                    >security@formalie.com</a
                  >
                </template>
                <template #policy>
                  <ULink
                    :to="`${localePath('/legal/acceptable-use')}#report`"
                    class="font-semibold underline underline-offset-4"
                  >
                    {{ t('legal.acceptableUse') }}
                  </ULink>
                </template>
              </i18n-t>
            </li>
            <li class="flex gap-3">
              <UIcon name="i-lucide-flag" class="mt-0.5 size-5 shrink-0" />
              <i18n-t keypath="trustPage.reportAbuse" tag="span" scope="global">
                <template #email>
                  <a href="mailto:abuse@formalie.com" class="font-semibold underline underline-offset-4"
                    >abuse@formalie.com</a
                  >
                </template>
              </i18n-t>
            </li>
            <li class="flex gap-3">
              <UIcon name="i-lucide-eye-off" class="mt-0.5 size-5 shrink-0" />
              <i18n-t keypath="trustPage.reportPrivacy" tag="span" scope="global">
                <template #email>
                  <a href="mailto:privacy@formalie.com" class="font-semibold underline underline-offset-4"
                    >privacy@formalie.com</a
                  >
                </template>
              </i18n-t>
            </li>
          </ul>
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
      </div>
    </UPageSection>

    <SiteCta />
  </div>
</template>
