<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.themes' })
const { t } = useI18n()
useHead({ title: () => t('nav.themes') })
</script>

<template>
  <AppPanel id="themes" :title="t('nav.themes')">
    <AppComingSoon icon="i-lucide-palette" title-key="nav.themes" />
  </AppPanel>
</template>
