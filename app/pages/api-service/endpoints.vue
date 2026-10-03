<!-- API service → endpoints (placeholder until F13; plan in PROGRESS.md → F13). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.apiEndpoints' })
const { t } = useI18n()
useHead({ title: () => t('nav.apiEndpoints') })
</script>

<template>
  <AppPanel id="api-endpoints" :title="t('nav.apiEndpoints')" :subtitle="t('apiService.section.endpoints')">
    <AppComingSoon icon="i-lucide-route" title-key="nav.apiEndpoints" description-key="apiService.section.endpoints" :back="{ labelKey: 'apiService.back', icon: 'i-lucide-layout-grid', to: '/api-service' }" />
  </AppPanel>
</template>
