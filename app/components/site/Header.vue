<script setup lang="ts">
import type { NavigationMenuItem } from '@nuxt/ui'

// The site header (docs/SITEMAP.md): logo, the menu with Product, Solutions and Resources panels, language,
// theme, Sign in and Start free. On phones the menu opens in a slide-over.
const { t } = useI18n()
const { main } = useSiteNav()
const links = useSiteLinks()

// Panels: two columns of icon tiles for long lists (reference 1, docs/DESIGN.md "Feature card"), one for short.
// The width is set on the panel itself, so the menu's viewport measures it correctly.
const wide = (item: NavigationMenuItem) => (item.children?.length ?? 0) > 4
const items = computed<NavigationMenuItem[]>(() =>
  main.value.map(item =>
    item.children ? { ...item, ui: { content: wide(item) ? 'sm:w-[40rem]' : 'sm:w-96' } } : item,
  ),
)
</script>

<template>
  <UHeader
    mode="slideover"
    :ui="{
      root: 'bg-default/80 backdrop-blur-md',
      // The full menu needs room for the longer languages, so it starts at xl (Nuxt UI's default is lg).
      center: 'hidden lg:hidden xl:flex',
      toggle: 'lg:inline-flex xl:hidden',
      content: 'lg:block xl:hidden',
    }"
  >
    <template #left>
      <SiteLogo />
    </template>

    <UNavigationMenu :items="items" content-orientation="vertical" :ui="{ viewport: 'shrink-0' }">
      <template #panel-content="{ item }">
        <ul class="grid gap-1 p-2" :class="wide(item) ? 'sm:grid-cols-2' : ''">
          <li v-for="child in (item as NavigationMenuItem).children" :key="child.label">
            <ULink
              :to="child.to"
              :target="child.target"
              class="group flex items-start gap-3 rounded-lg p-3 transition-colors hover:bg-elevated focus-visible:bg-elevated"
            >
              <span
                class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-inverted text-inverted transition-transform motion-safe:group-hover:-translate-y-0.5"
              >
                <UIcon :name="child.icon!" class="size-4" />
              </span>
              <span class="min-w-0">
                <span class="block text-sm font-semibold text-highlighted">{{ child.label }}</span>
                <span class="mt-0.5 line-clamp-2 block text-sm text-muted">{{ child.description }}</span>
              </span>
            </ULink>
          </li>
        </ul>
      </template>
    </UNavigationMenu>

    <template #right>
      <div class="hidden items-center gap-1 xl:flex">
        <SiteLanguageSwitch />
        <SiteThemeSwitch />
      </div>
      <UButton
        :to="links.signIn"
        :label="t('nav.signIn')"
        color="neutral"
        variant="outline"
        class="hidden sm:inline-flex"
      />
      <UButton :to="links.signup('starter')" :label="t('nav.startFree')" color="neutral" />
    </template>

    <template #body>
      <UNavigationMenu :items="main" orientation="vertical" class="-mx-2.5" />
      <USeparator class="my-6" />
      <div class="flex flex-col gap-3">
        <UButton :to="links.signIn" :label="t('nav.signIn')" color="neutral" variant="outline" block />
        <UButton :to="links.signup('starter')" :label="t('nav.startFree')" color="neutral" block />
      </div>
      <div class="mt-6 flex items-center justify-between">
        <SiteLanguageSwitch show-name />
        <SiteThemeSwitch />
      </div>
    </template>
  </UHeader>
</template>
