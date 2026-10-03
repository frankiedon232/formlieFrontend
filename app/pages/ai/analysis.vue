<!-- AI assistant → analysis (placeholder until F19; plan in PROGRESS.md → F19). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.aiAnalysis' })
const { t } = useI18n()
useHead({ title: () => t('nav.aiAnalysis') })
</script>

<template>
  <AppPanel id="ai-analysis" :title="t('nav.aiAnalysis')" :subtitle="t('ai.section.analysis')">
    <AppComingSoon icon="i-lucide-chart-scatter" title-key="nav.aiAnalysis" description-key="ai.section.analysis" :back="{ labelKey: 'ai.back', icon: 'i-lucide-layout-grid', to: '/ai' }" />
  </AppPanel>
</template>
