<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.destinations' })
const { t } = useI18n()
useHead({ title: () => t('nav.destinations') })
</script>

<template>
  <AppPanel id="destinations" :title="t('nav.destinations')">
    <AppComingSoon icon="i-lucide-database" title-key="nav.destinations" />
  </AppPanel>
</template>
