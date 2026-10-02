<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.optionSets' })
const { t } = useI18n()
useHead({ title: () => t('nav.optionSets') })
</script>

<template>
  <AppPanel id="option-sets">
    <AppComingSoon icon="i-lucide-list-checks" title-key="nav.optionSets" />
  </AppPanel>
</template>
