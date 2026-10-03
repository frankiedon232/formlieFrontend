<!-- API service → access (placeholder until F13; plan in PROGRESS.md → F13). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.apiAccess' })
const { t } = useI18n()
useHead({ title: () => t('nav.apiAccess') })
</script>

<template>
  <AppPanel id="api-access" :title="t('nav.apiAccess')" :subtitle="t('apiService.section.access')">
    <AppComingSoon icon="i-lucide-shield-check" title-key="nav.apiAccess" description-key="apiService.section.access" :back="{ labelKey: 'apiService.back', icon: 'i-lucide-layout-grid', to: '/api-service' }" />
  </AppPanel>
</template>
