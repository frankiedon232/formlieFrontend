<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.responses' })
const { t } = useI18n()
useHead({ title: () => t('nav.responses') })
</script>

<template>
  <AppPanel id="responses">
    <AppComingSoon icon="i-lucide-inbox" title-key="nav.responses" />
  </AppPanel>
</template>
