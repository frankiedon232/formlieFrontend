<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.templates' })
const { t } = useI18n()
useHead({ title: () => t('nav.templates') })
</script>

<template>
  <AppPanel id="templates" :title="t('nav.templates')">
    <AppComingSoon icon="i-lucide-layout-template" title-key="nav.templates" />
  </AppPanel>
</template>
