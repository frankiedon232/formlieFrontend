<!-- API service → app integrations (placeholder; plan in PROGRESS.md → F13). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.apiApps' })
const { t } = useI18n()
useHead({ title: () => t('nav.apiApps') })
</script>

<template>
  <AppPanel id="api-apps" :title="t('nav.apiApps')" :subtitle="t('apiService.section.apps')">
    <AppComingSoon icon="i-lucide-blocks" title-key="nav.apiApps" description-key="apiService.section.apps" :back="{ labelKey: 'apiService.back', icon: 'i-lucide-layout-grid', to: '/api-service' }" />
  </AppPanel>
</template>
