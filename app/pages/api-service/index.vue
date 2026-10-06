<!--
  API service overview (own rail area, F13). Placeholder: what each section will do, the three
  ways a form collects data (link, embed, API) and what an endpoint address looks like.
  The full plan is in PROGRESS.md → F13.
-->
<script setup lang="ts">
import { API_METHODS, apiEndpointUrl } from '#shared/utils/urls/public'

definePageMeta({ breadcrumb: 'nav.apiService' })
const { t } = useI18n()
useHead({ title: () => t('nav.apiService') })
const config = useRuntimeConfig().public

const sections = [
  { key: 'services', nav: 'apiServices', icon: 'i-lucide-boxes', to: '/api-service/services', live: true },
  { key: 'endpoints', nav: 'apiEndpoints', icon: 'i-lucide-route', to: '/api-service/endpoints', live: true },
  { key: 'auth', nav: 'apiAuth', icon: 'i-lucide-key-round', to: '/api-service/auth', live: true },
  { key: 'access', nav: 'apiAccess', icon: 'i-lucide-shield-check', to: '/api-service/access' },
  { key: 'logs', nav: 'apiLogs', icon: 'i-lucide-scroll-text', to: '/api-service/logs' },
  { key: 'analytics', nav: 'apiAnalytics', icon: 'i-lucide-chart-line', to: '/api-service/analytics' },
  { key: 'docs', nav: 'apiDocs', icon: 'i-lucide-book-open', to: '/api-service/docs' },
]
const channels = [
  { key: 'link', icon: 'i-lucide-link' },
  { key: 'embed', icon: 'i-lucide-code' },
  { key: 'api', icon: 'i-lucide-code-xml' },
]
// Example only: a made-up organisation key and endpoint name.
const example = apiEndpointUrl(config.apiServiceUrl, 'k7Qm2xP9aZ', 'register-account')
</script>

<template>
  <AppPanel id="api-service" :title="t('nav.apiService')" :subtitle="t('apiService.subtitle')">
    <UCard variant="outline" class="shrink-0">
      <div class="flex flex-col gap-4">
        <div>
          <p class="text-sm font-medium text-highlighted">{{ t('apiService.channels.title') }}</p>
          <p class="text-sm text-muted">{{ t('apiService.channels.hint') }}</p>
        </div>
        <div class="grid gap-2 sm:grid-cols-3">
          <div v-for="channel in channels" :key="channel.key" class="flex items-center gap-2 rounded-md border border-default p-3">
            <UIcon :name="channel.icon" class="size-5 shrink-0 text-default" />
            <span class="text-sm font-medium text-highlighted">{{ t(`apiService.channels.${channel.key}`) }}</span>
          </div>
        </div>
        <div class="flex flex-col gap-1.5">
          <p class="text-xs font-medium text-muted uppercase">{{ t('apiService.example') }}</p>
          <div class="flex flex-wrap items-center gap-1.5">
            <UBadge v-for="method in API_METHODS" :key="method" :label="method" color="neutral" variant="outline" class="font-mono" />
          </div>
          <code class="block overflow-x-auto rounded-md bg-elevated px-3 py-2 font-mono text-sm text-highlighted">{{ example }}</code>
        </div>
      </div>
    </UCard>

    <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <UPageCard
        v-for="section in sections"
        :key="section.key"
        :to="section.to"
        :icon="section.icon"
        :title="t(`nav.${section.nav}`)"
        :description="t(`apiService.section.${section.key}`)"
        variant="outline"
        :ui="{ leadingIcon: 'size-5 text-default' }"
      >
        <template v-if="!('live' in section)" #footer>
          <UBadge :label="t('placeholder.title')" color="neutral" variant="soft" size="sm" />
        </template>
      </UPageCard>
    </div>
  </AppPanel>
</template>
