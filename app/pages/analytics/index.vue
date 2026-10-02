<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.analytics' })
const { t } = useI18n()
useHead({ title: () => t('nav.analytics') })
</script>

<template>
  <AppPanel id="analytics" :title="t('nav.analytics')">
    <AppComingSoon icon="i-lucide-chart-column" title-key="nav.analytics" />
  </AppPanel>
</template>
