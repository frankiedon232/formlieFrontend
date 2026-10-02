<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.settings' })
const { t } = useI18n()
useHead({ title: () => t('nav.settings') })
</script>

<template>
  <AppPanel id="settings" :title="t('nav.settings')">
    <AppComingSoon icon="i-lucide-settings" title-key="nav.settings" />
  </AppPanel>
</template>
