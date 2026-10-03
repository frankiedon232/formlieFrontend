<!-- API service → analytics (placeholder until F13; plan in PROGRESS.md → F13). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.apiAnalytics' })
const { t } = useI18n()
useHead({ title: () => t('nav.apiAnalytics') })
</script>

<template>
  <AppPanel id="api-analytics" :title="t('nav.apiAnalytics')" :subtitle="t('apiService.section.analytics')">
    <AppComingSoon icon="i-lucide-chart-line" title-key="nav.apiAnalytics" description-key="apiService.section.analytics" :back="{ labelKey: 'apiService.back', icon: 'i-lucide-layout-grid', to: '/api-service' }" />
  </AppPanel>
</template>
