<!-- Data sources → dataConnections (placeholder until F12; plan in PROGRESS.md → F12). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.dataConnections' })
const { t } = useI18n()
useHead({ title: () => t('nav.dataConnections') })
</script>

<template>
  <AppPanel id="data-connections" :title="t('nav.dataConnections')" :subtitle="t('dataSources.section.connections')">
    <AppComingSoon icon="i-lucide-database" title-key="nav.dataConnections" description-key="dataSources.section.connections" :back="{ labelKey: 'dataSources.back', icon: 'i-lucide-layout-grid', to: '/data-sources' }" />
  </AppPanel>
</template>
