<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.apiKeys' })
const { t } = useI18n()
useHead({ title: () => t('nav.apiKeys') })
</script>

<template>
  <AppPanel id="api-keys" :title="t('nav.apiKeys')">
    <AppComingSoon icon="i-lucide-key-round" title-key="nav.apiKeys" />
  </AppPanel>
</template>
