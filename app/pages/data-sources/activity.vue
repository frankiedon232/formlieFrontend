<!-- Data sources → dataActivity (placeholder until F12; plan in PROGRESS.md → F12). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.dataActivity' })
const { t } = useI18n()
useHead({ title: () => t('nav.dataActivity') })
</script>

<template>
  <AppPanel id="data-activity" :title="t('nav.dataActivity')" :subtitle="t('dataSources.section.activity')">
    <AppComingSoon icon="i-lucide-activity" title-key="nav.dataActivity" description-key="dataSources.section.activity" :back="{ labelKey: 'dataSources.back', icon: 'i-lucide-layout-grid', to: '/data-sources' }" />
  </AppPanel>
</template>
