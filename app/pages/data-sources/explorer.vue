<!-- Data sources → dataExplorer (placeholder until F12; plan in PROGRESS.md → F12). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.dataExplorer' })
const { t } = useI18n()
useHead({ title: () => t('nav.dataExplorer') })
</script>

<template>
  <AppPanel id="data-explorer" :title="t('nav.dataExplorer')" :subtitle="t('dataSources.section.explorer')">
    <AppComingSoon icon="i-lucide-table-2" title-key="nav.dataExplorer" description-key="dataSources.section.explorer" :back="{ labelKey: 'dataSources.back', icon: 'i-lucide-layout-grid', to: '/data-sources' }" />
  </AppPanel>
</template>
