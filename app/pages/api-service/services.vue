<!-- API service → services (placeholder until F13; plan in PROGRESS.md → F13). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.apiServices' })
const { t } = useI18n()
useHead({ title: () => t('nav.apiServices') })
</script>

<template>
  <AppPanel id="api-services" :title="t('nav.apiServices')" :subtitle="t('apiService.section.services')">
    <AppComingSoon icon="i-lucide-boxes" title-key="nav.apiServices" description-key="apiService.section.services" :back="{ labelKey: 'apiService.back', icon: 'i-lucide-layout-grid', to: '/api-service' }" />
  </AppPanel>
</template>
