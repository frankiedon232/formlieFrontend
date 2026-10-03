<!-- API service → docs (placeholder until F13; plan in PROGRESS.md → F13). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.apiDocs' })
const { t } = useI18n()
useHead({ title: () => t('nav.apiDocs') })
</script>

<template>
  <AppPanel id="api-docs" :title="t('nav.apiDocs')" :subtitle="t('apiService.section.docs')">
    <AppComingSoon icon="i-lucide-book-open" title-key="nav.apiDocs" description-key="apiService.section.docs" :back="{ labelKey: 'apiService.back', icon: 'i-lucide-layout-grid', to: '/api-service' }" />
  </AppPanel>
</template>
