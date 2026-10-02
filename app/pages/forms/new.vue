<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.newForm' })
const { t } = useI18n()
useHead({ title: () => t('nav.newForm') })
</script>

<template>
  <AppPanel id="forms-new" :title="t('nav.newForm')">
    <AppComingSoon icon="i-lucide-file-plus" title-key="nav.newForm" />
  </AppPanel>
</template>
