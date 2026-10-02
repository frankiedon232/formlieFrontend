<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.webhooks' })
const { t } = useI18n()
useHead({ title: () => t('nav.webhooks') })
</script>

<template>
  <AppPanel id="webhooks">
    <AppComingSoon icon="i-lucide-webhook" title-key="nav.webhooks" />
  </AppPanel>
</template>
