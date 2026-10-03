<!-- AI assistant → insights (placeholder until F19; plan in PROGRESS.md → F19). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.aiInsights' })
const { t } = useI18n()
useHead({ title: () => t('nav.aiInsights') })
</script>

<template>
  <AppPanel id="ai-insights" :title="t('nav.aiInsights')" :subtitle="t('ai.section.insights')">
    <AppComingSoon icon="i-lucide-lightbulb" title-key="nav.aiInsights" description-key="ai.section.insights" :back="{ labelKey: 'ai.back', icon: 'i-lucide-layout-grid', to: '/ai' }" />
  </AppPanel>
</template>
