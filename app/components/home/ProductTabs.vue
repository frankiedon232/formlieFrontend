<script setup lang="ts">
import type { TabsItem } from '@nuxt/ui'

// Product tabs after reference 3: a tab per area, a big card with the story, four points, two buttons and a real
// screenshot in a browser frame (docs/DESIGN.md "Using the screenshots"). Dark screens in dark mode where they exist.
const { t, tm, rt } = useI18n()
const localePath = useLocalePath()
const links = useSiteLinks()

const TABS = [
  {
    key: 'build',
    icon: 'i-lucide-layout-template',
    shot: 'form-builder',
    dark: true,
    width: 2320,
    height: 1800,
    page: '/features/form-builder',
  },
  {
    key: 'design',
    icon: 'i-lucide-palette',
    shot: 'form-design',
    dark: true,
    width: 2320,
    height: 1800,
    page: '/features/design',
  },
  {
    key: 'responses',
    icon: 'i-lucide-inbox',
    shot: 'responses',
    dark: true,
    width: 2320,
    height: 1180,
    page: '/features/responses',
  },
  {
    key: 'data',
    icon: 'i-lucide-database',
    shot: 'data-sources',
    dark: true,
    width: 2320,
    height: 1300,
    page: '/features/data-sources',
  },
  // api-service rather than api-docs: the docs shot shows a development API address (owner to confirm).
  {
    key: 'api',
    icon: 'i-lucide-braces',
    shot: 'api-service',
    dark: true,
    width: 2320,
    height: 1300,
    page: '/features/api-service',
  },
] as const

const items = computed<TabsItem[]>(() =>
  TABS.map(tab => ({
    label: t(`home.tabs.${tab.key}.label`),
    icon: tab.icon,
    value: tab.key,
    slot: 'panel' as const,
  })),
)

const points = (key: string) => (tm(`home.tabs.${key}.points`) as unknown[]).map(point => rt(point as string))
const tabOf = (value: unknown) => TABS.find(tab => tab.key === value) ?? TABS[0]
</script>

<template>
  <UPageSection
    :headline="t('home.tabs.eyebrow')"
    :title="t('home.tabs.title')"
    :description="t('home.tabs.description')"
  >
    <UTabs
      :items="items"
      default-value="build"
      color="neutral"
      variant="pill"
      size="lg"
      :ui="{
        list: 'mx-auto w-full max-w-3xl overflow-x-auto bg-elevated/60 ring-1 ring-default',
        trigger: 'grow min-w-fit',
        content: 'mt-8',
      }"
    >
      <template #panel="{ item }">
        <div
          v-for="tab in [tabOf((item as TabsItem).value)]"
          :key="tab.key"
          class="grid items-center gap-10 overflow-hidden rounded-3xl bg-default p-6 shadow-xl shadow-black/5 ring-1 ring-default motion-safe:animate-rise sm:p-10 lg:grid-cols-[2fr_3fr]"
        >
          <div>
            <h3 class="text-2xl font-semibold tracking-tight text-highlighted sm:text-3xl">
              {{ t(`home.tabs.${tab.key}.title`) }}
            </h3>
            <p class="mt-3 text-muted">{{ t(`home.tabs.${tab.key}.text`) }}</p>
            <ul class="mt-6 space-y-3">
              <li v-for="point in points(tab.key)" :key="point" class="flex gap-3 text-sm text-toned">
                <span
                  class="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-inverted text-inverted"
                >
                  <UIcon name="i-lucide-check" class="size-3" />
                </span>
                {{ point }}
              </li>
            </ul>
            <div class="mt-8 flex flex-wrap gap-3">
              <UButton :to="links.signup('starter')" :label="t('nav.startFree')" color="neutral" size="lg" />
              <UButton
                :to="localePath(tab.page)"
                :label="t('home.tabs.seeHow')"
                color="neutral"
                variant="outline"
                size="lg"
                trailing-icon="i-lucide-arrow-right"
              />
            </div>
          </div>

          <!-- The screenshot in a browser frame, slightly lifted -->
          <div class="relative">
            <div aria-hidden="true" class="absolute -inset-6 -z-0 rounded-[2rem] bg-violet-500/10 blur-2xl" />
            <figure
              class="relative overflow-hidden rounded-2xl bg-elevated shadow-2xl shadow-black/10 ring-1 ring-default"
            >
              <div class="flex items-center gap-1.5 border-b border-default px-3 py-2">
                <span class="size-2.5 rounded-full bg-accented" />
                <span class="size-2.5 rounded-full bg-accented" />
                <span class="size-2.5 rounded-full bg-accented" />
              </div>
              <NuxtImg
                :src="`/screenshots/${tab.shot}.webp`"
                :alt="t(`home.tabs.${tab.key}.alt`)"
                :width="tab.width"
                :height="tab.height"
                sizes="sm:100vw md:90vw lg:640px"
                class="block h-auto w-full"
                :class="{ 'dark:hidden': tab.dark }"
                loading="lazy"
              />
              <NuxtImg
                v-if="tab.dark"
                :src="`/screenshots/${tab.shot}-dark.webp`"
                :alt="t(`home.tabs.${tab.key}.alt`)"
                :width="tab.width"
                :height="tab.height"
                sizes="sm:100vw md:90vw lg:640px"
                class="hidden h-auto w-full dark:block"
                loading="lazy"
              />
            </figure>
          </div>
        </div>
      </template>
    </UTabs>
  </UPageSection>
</template>
