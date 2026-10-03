<!-- API service → logs (placeholder until F13; plan in PROGRESS.md → F13). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.apiLogs' })
const { t } = useI18n()
useHead({ title: () => t('nav.apiLogs') })
</script>

<template>
  <AppPanel id="api-logs" :title="t('nav.apiLogs')" :subtitle="t('apiService.section.logs')">
    <AppComingSoon icon="i-lucide-scroll-text" title-key="nav.apiLogs" description-key="apiService.section.logs" :back="{ labelKey: 'apiService.back', icon: 'i-lucide-layout-grid', to: '/api-service' }" />
  </AppPanel>
</template>
