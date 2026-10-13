<script setup lang="ts">
import type { FooterColumn } from '@nuxt/ui'

// A clean white footer with muted links (reference 2): four columns, the legal row, language, theme and ©.
const { t } = useI18n()
const localePath = useLocalePath()
const { product, solutions, resources, company, legal } = useSiteNav()
// Status page, social profiles and legal entity from the platform admin, each shown only once it is set.
const platform = usePlatform()
const social = computed(() => platform.value.social.map(item => ({ ...item, ...SOCIAL_META[item.network] })))

const plain = (items: { label?: string; to?: unknown; target?: unknown }[]) =>
  items.map(({ label, to, target }) => ({ label, to, target })) as FooterColumn['children']

const columns = computed<FooterColumn[]>(() => [
  {
    label: t('nav.product'),
    children: plain([
      ...product.value,
      { label: t('nav.pricing'), to: localePath('/pricing') },
      { label: t('nav.integrations'), to: localePath('/integrations') },
    ]),
  },
  { label: t('nav.solutions'), children: plain(solutions.value) },
  { label: t('nav.resources'), children: plain(resources.value) },
  { label: t('company.title'), children: plain(company.value) },
])

const year = new Date().getFullYear()
</script>

<template>
  <footer class="border-t border-default">
    <UContainer class="grid gap-10 py-12 lg:grid-cols-[1fr_3fr] lg:py-16">
      <div class="flex flex-col gap-4">
        <SiteLogo />
        <p class="max-w-xs text-sm text-muted">{{ t('footer.tagline') }}</p>
      </div>
      <UFooterColumns :columns="columns" :ui="{ root: 'xl:grid-cols-4', center: 'xl:col-span-4' }" />
    </UContainer>

    <UFooter :ui="{ root: 'border-t border-default', top: 'py-0 lg:py-0' }">
      <template #left>
        <div class="flex flex-col gap-1 text-sm text-muted">
          <p class="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span>{{ t('footer.copyright', { year }) }}</span>
            <ULink
              v-if="platform.statusUrl"
              :to="platform.statusUrl"
              target="_blank"
              class="inline-flex items-center gap-1.5 text-muted hover:text-highlighted"
            >
              <span class="size-1.5 rounded-full bg-emerald-500" />{{ t('footer.status') }}
            </ULink>
          </p>
          <p v-if="platform.legalEntity.name" class="text-xs text-dimmed">
            {{ [platform.legalEntity.name, platform.legalEntity.address].filter(Boolean).join(', ') }}
          </p>
        </div>
      </template>

      <nav :aria-label="t('legal.title')">
        <ul class="flex flex-wrap justify-center gap-x-4 gap-y-2 text-sm">
          <li v-for="item in legal" :key="String(item.to)">
            <ULink :to="item.to" class="text-muted hover:text-highlighted">{{ item.label }}</ULink>
          </li>
        </ul>
      </nav>

      <template #right>
        <UButton
          v-for="item in social"
          :key="item.network"
          :to="item.url"
          target="_blank"
          rel="noopener me"
          :icon="item.icon"
          :aria-label="item.name"
          color="neutral"
          variant="ghost"
        />
        <SiteLanguageSwitch show-name />
        <SiteThemeSwitch />
      </template>
    </UFooter>
  </footer>
</template>
