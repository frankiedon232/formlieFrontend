<!-- Data sources → dataQuery (placeholder until F12; plan in PROGRESS.md → F12). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.dataQuery' })
const { t } = useI18n()
useHead({ title: () => t('nav.dataQuery') })
</script>

<template>
  <AppPanel id="data-query" :title="t('nav.dataQuery')" :subtitle="t('dataSources.section.query')">
    <AppComingSoon icon="i-lucide-square-terminal" title-key="nav.dataQuery" description-key="dataSources.section.query" :back="{ labelKey: 'dataSources.back', icon: 'i-lucide-layout-grid', to: '/data-sources' }" />
  </AppPanel>
</template>
