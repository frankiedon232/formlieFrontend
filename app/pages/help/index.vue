<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.help' })
const { t } = useI18n()
useHead({ title: () => t('nav.help') })
</script>

<template>
  <AppPanel id="help" :title="t('nav.help')">
    <AppComingSoon icon="i-lucide-circle-help" title-key="nav.help" />
  </AppPanel>
</template>
