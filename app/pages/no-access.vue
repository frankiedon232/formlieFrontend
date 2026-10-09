<!-- Roles & access (F22): a page the person's role doesn't open. Says so and offers the way back. -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'access.title' })
const { t } = useI18n()
useHead({ title: () => t('access.title') })
</script>

<template>
  <AppPanel id="no-access" :title="t('access.title')">
    <AppEmpty icon="i-lucide-lock-keyhole" :title="t('access.title')" :description="t('access.desc')" :actions="[{ label: t('nav.forms'), icon: 'i-lucide-file-text', color: 'neutral', variant: 'outline', to: '/forms' }]" />
  </AppPanel>
</template>
