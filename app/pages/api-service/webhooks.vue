<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.webhooks' })
const { t } = useI18n()
useHead({ title: () => t('nav.webhooks') })
</script>

<template>
  <AppPanel id="webhooks" :title="t('nav.webhooks')">
    <AppComingSoon icon="i-lucide-webhook" title-key="nav.webhooks" description-key="apiService.section.webhooks" :back="{ labelKey: 'apiService.back', icon: 'i-lucide-layout-grid', to: '/api-service' }" />
  </AppPanel>
</template>
