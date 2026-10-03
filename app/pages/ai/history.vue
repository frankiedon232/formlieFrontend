<!-- AI assistant → history (placeholder until F19; plan in PROGRESS.md → F19). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.aiHistory' })
const { t } = useI18n()
useHead({ title: () => t('nav.aiHistory') })
</script>

<template>
  <AppPanel id="ai-history" :title="t('nav.aiHistory')" :subtitle="t('ai.section.history')">
    <AppComingSoon icon="i-lucide-history" title-key="nav.aiHistory" description-key="ai.section.history" :back="{ labelKey: 'ai.back', icon: 'i-lucide-layout-grid', to: '/ai' }" />
  </AppPanel>
</template>
