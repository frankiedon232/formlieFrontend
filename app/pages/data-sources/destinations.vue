<!-- Data sources → destinations (placeholder until F12; plan in PROGRESS.md → F12). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.destinations' })
const { t } = useI18n()
useHead({ title: () => t('nav.destinations') })
</script>

<template>
  <AppPanel id="data-destinations" :title="t('nav.destinations')" :subtitle="t('dataSources.section.destinations')">
    <AppComingSoon icon="i-lucide-send" title-key="nav.destinations" description-key="dataSources.section.destinations" :back="{ labelKey: 'dataSources.back', icon: 'i-lucide-layout-grid', to: '/data-sources' }" />
  </AppPanel>
</template>
