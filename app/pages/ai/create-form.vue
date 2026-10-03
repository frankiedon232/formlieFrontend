<!-- AI assistant → create-form (placeholder until F19; plan in PROGRESS.md → F19). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.aiCreateForm' })
const { t } = useI18n()
useHead({ title: () => t('nav.aiCreateForm') })
</script>

<template>
  <AppPanel id="ai-create-form" :title="t('nav.aiCreateForm')" :subtitle="t('ai.section.createForm')">
    <AppComingSoon icon="i-lucide-file-plus-2" title-key="nav.aiCreateForm" description-key="ai.section.createForm" :back="{ labelKey: 'ai.back', icon: 'i-lucide-layout-grid', to: '/ai' }" />
  </AppPanel>
</template>
