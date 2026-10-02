<!-- Data sources → dataTransfers (placeholder until F12; plan in PROGRESS.md → F12). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.dataTransfers' })
const { t } = useI18n()
useHead({ title: () => t('nav.dataTransfers') })
</script>

<template>
  <AppPanel id="data-transfers" :title="t('nav.dataTransfers')" :subtitle="t('dataSources.section.transfers')">
    <AppComingSoon icon="i-lucide-arrow-left-right" title-key="nav.dataTransfers" description-key="dataSources.section.transfers" :back="{ labelKey: 'dataSources.back', icon: 'i-lucide-layout-grid', to: '/data-sources' }" />
  </AppPanel>
</template>
