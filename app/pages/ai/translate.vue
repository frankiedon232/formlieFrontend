<!-- AI assistant → translate (placeholder until F19; plan in PROGRESS.md → F19). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.aiTranslate' })
const { t } = useI18n()
useHead({ title: () => t('nav.aiTranslate') })
</script>

<template>
  <AppPanel id="ai-translate" :title="t('nav.aiTranslate')" :subtitle="t('ai.section.translate')">
    <AppComingSoon icon="i-lucide-languages" title-key="nav.aiTranslate" description-key="ai.section.translate" :back="{ labelKey: 'ai.back', icon: 'i-lucide-layout-grid', to: '/ai' }" />
  </AppPanel>
</template>
