<!-- AI assistant → settings (placeholder until F19; plan in PROGRESS.md → F19). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.aiSettings' })
const { t } = useI18n()
useHead({ title: () => t('nav.aiSettings') })
</script>

<template>
  <AppPanel id="ai-settings" :title="t('nav.aiSettings')" :subtitle="t('ai.section.settings')">
    <AppComingSoon icon="i-lucide-sliders-horizontal" title-key="nav.aiSettings" description-key="ai.section.settings" :back="{ labelKey: 'ai.back', icon: 'i-lucide-layout-grid', to: '/ai' }" />
  </AppPanel>
</template>
