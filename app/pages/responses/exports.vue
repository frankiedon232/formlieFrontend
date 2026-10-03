<!-- Responses → exports (placeholder until F11: export jobs with progress and download). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.responsesExports' })
const { t } = useI18n()
useHead({ title: () => t('nav.responsesExports') })
</script>

<template>
  <AppPanel id="responses-exports" :title="t('nav.responsesExports')">
    <AppComingSoon icon="i-lucide-file-down" title-key="nav.responsesExports" />
  </AppPanel>
</template>
