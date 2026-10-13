<script setup lang="ts">
// Integrations (docs/SITEMAP.md): databases, API service and webhooks, sign-in providers, open standards.
const { t } = useI18n()
const localePath = useLocalePath()

const DATABASES = [
  { name: 'MySQL', icon: 'i-simple-icons-mysql' },
  { name: 'MariaDB', icon: 'i-simple-icons-mariadb' },
  { name: 'PostgreSQL', icon: 'i-simple-icons-postgresql' },
  { name: 'SQL Server', icon: 'i-simple-icons-microsoftsqlserver' },
  { name: 'Oracle', icon: 'i-simple-icons-oracle' },
]
const SIGNIN = [
  { name: 'Google', icon: 'i-simple-icons-google' },
  { name: 'Facebook', icon: 'i-simple-icons-facebook' },
  { name: 'Okta', icon: 'i-simple-icons-okta' },
  { name: 'Microsoft Entra ID', icon: 'i-simple-icons-microsoft' },
  { name: 'Google Workspace', icon: 'i-simple-icons-google' },
  { name: 'OneLogin', icon: 'i-lucide-key-round' },
  { name: 'SAML 2.0', icon: 'i-lucide-shield-check' },
  { name: 'OpenID Connect', icon: 'i-simple-icons-openid' },
]
const API = [
  { name: 'REST API', icon: 'i-lucide-braces' },
  { name: 'Webhooks', icon: 'i-lucide-webhook' },
  { name: 'JSON', icon: 'i-simple-icons-json' },
]
const STANDARDS = ['SQL', 'REST', 'JSON', 'SAML 2.0', 'OpenID Connect', 'HTTPS']

const groups = computed(() => [
  { key: 'databases', icon: 'i-lucide-database', items: DATABASES, link: '/features/data-sources' },
  { key: 'api', icon: 'i-lucide-braces', items: API, link: '/features/api-service' },
  { key: 'signin', icon: 'i-lucide-log-in', items: SIGNIN, link: '/features/access-control' },
])

usePageSeo({
  title: () => t('nav.integrations'),
  description: () => t('integrationsPage.metaDescription'),
  breadcrumbs: () => [{ name: t('nav.integrations'), path: '/integrations' }],
})
</script>

<template>
  <div>
    <div class="relative isolate overflow-hidden">
      <div aria-hidden="true" class="absolute inset-x-0 -top-40 -z-10 flex justify-center">
        <div class="h-[26rem] w-[50rem] rounded-full bg-violet-500/10 blur-3xl dark:bg-violet-500/15" />
      </div>
      <UPageHero
        :title="t('integrationsPage.title')"
        :description="t('integrationsPage.description')"
        :ui="{
          container: 'pb-6 sm:pb-8 lg:pb-10',
          title: 'text-balance',
        }"
      >
        <template #headline>
          <UBadge
            :label="t('nav.integrations')"
            icon="i-lucide-plug"
            color="neutral"
            variant="outline"
            size="lg"
            class="rounded-full px-3"
          />
        </template>
        <!-- Logos drifting past -->
        <UMarquee pause-on-hover :overlay="true" :ui="{ root: '[--duration:40s] [--gap:--spacing(3)]' }">
          <span
            v-for="item in [...DATABASES, ...SIGNIN, ...API]"
            :key="item.name"
            class="flex items-center gap-2 rounded-full bg-default px-4 py-2 text-sm font-medium whitespace-nowrap text-highlighted shadow-sm ring-1 ring-default"
          >
            <UIcon :name="item.icon" class="size-5" />
            {{ item.name }}
          </span>
        </UMarquee>
      </UPageHero>
    </div>

    <UPageSection :ui="{ container: 'pt-0 sm:pt-0 lg:pt-0 gap-6 sm:gap-6 lg:gap-6' }">
      <div
        v-for="group in groups"
        :key="group.key"
        class="grid items-start gap-8 rounded-3xl bg-default p-6 shadow-xl shadow-black/5 ring-1 ring-default sm:p-10 lg:grid-cols-[1fr_2fr]"
      >
        <div>
          <span class="flex size-11 items-center justify-center rounded-xl bg-inverted text-inverted">
            <UIcon :name="group.icon" class="size-5" />
          </span>
          <h2 class="mt-5 text-2xl font-semibold tracking-tight text-highlighted">
            {{ t(`integrationsPage.${group.key}.title`) }}
          </h2>
          <p class="mt-2 text-muted">{{ t(`integrationsPage.${group.key}.text`) }}</p>
          <UButton
            :to="localePath(group.link)"
            :label="t('common.learnMore')"
            color="neutral"
            variant="link"
            trailing-icon="i-lucide-arrow-right"
            class="mt-4 px-0"
          />
        </div>
        <ul class="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <li
            v-for="(item, i) in group.items"
            :key="item.name"
            class="flex items-center gap-3 rounded-xl bg-elevated/50 p-4 ring-1 ring-default motion-safe:animate-rise"
            :style="{ animationDelay: `${i * 60}ms` }"
          >
            <UIcon :name="item.icon" class="size-6 shrink-0 text-highlighted" />
            <span class="text-sm font-medium text-highlighted">{{ item.name }}</span>
          </li>
        </ul>
      </div>
    </UPageSection>

    <UPageSection
      :title="t('integrationsPage.standards.title')"
      :description="t('integrationsPage.standards.text')"
      orientation="horizontal"
    >
      <template #links>
        <ul class="flex flex-wrap gap-2">
          <li v-for="item in STANDARDS" :key="item">
            <UBadge
              :label="item"
              color="neutral"
              variant="outline"
              size="lg"
              class="rounded-full font-mono"
            />
          </li>
        </ul>
      </template>
      <SiteScreenFrame
        :shot="{ file: 'data-connections', width: 2320, height: 1300, dark: false }"
        :alt="t('integrationsPage.alt')"
      />
    </UPageSection>

    <LazySiteCta hydrate-on-visible />
  </div>
</template>
