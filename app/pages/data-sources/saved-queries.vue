<!-- Data sources → dataSavedQueries (placeholder until F12; plan in PROGRESS.md → F12). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.dataSavedQueries' })
const { t } = useI18n()
useHead({ title: () => t('nav.dataSavedQueries') })
</script>

<template>
  <AppPanel id="data-saved-queries" :title="t('nav.dataSavedQueries')" :subtitle="t('dataSources.section.savedQueries')">
    <AppComingSoon icon="i-lucide-bookmark" title-key="nav.dataSavedQueries" description-key="dataSources.section.savedQueries" :back="{ labelKey: 'dataSources.back', icon: 'i-lucide-layout-grid', to: '/data-sources' }" />
  </AppPanel>
</template>
