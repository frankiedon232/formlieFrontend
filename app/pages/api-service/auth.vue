<!-- API service → auth (placeholder until F13; plan in PROGRESS.md → F13). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.apiAuth' })
const { t } = useI18n()
useHead({ title: () => t('nav.apiAuth') })
</script>

<template>
  <AppPanel id="api-auth" :title="t('nav.apiAuth')" :subtitle="t('apiService.section.auth')">
    <AppComingSoon icon="i-lucide-key-round" title-key="nav.apiAuth" description-key="apiService.section.auth" :back="{ labelKey: 'apiService.back', icon: 'i-lucide-layout-grid', to: '/api-service' }" />
  </AppPanel>
</template>
