<script setup lang="ts">
definePageMeta({ breadcrumb: 'user.profile' })
const { t } = useI18n()
useHead({ title: () => t('user.profile') })
</script>

<template>
  <AppPanel id="profile">
    <AppComingSoon icon="i-lucide-circle-user" title-key="user.profile" />
  </AppPanel>
</template>
