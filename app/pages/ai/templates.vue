<!-- AI assistant → templates (placeholder until F19; plan in PROGRESS.md → F19). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.aiTemplates' })
const { t } = useI18n()
useHead({ title: () => t('nav.aiTemplates') })
</script>

<template>
  <AppPanel id="ai-templates" :title="t('nav.aiTemplates')" :subtitle="t('ai.section.templates')">
    <AppComingSoon icon="i-lucide-layout-template" title-key="nav.aiTemplates" description-key="ai.section.templates" :back="{ labelKey: 'ai.back', icon: 'i-lucide-layout-grid', to: '/ai' }" />
  </AppPanel>
</template>
