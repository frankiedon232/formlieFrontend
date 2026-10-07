<!-- Settings → Job titles (F14 M2): what people do (not permission roles, F22), with who holds each. -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'settings.nav.jobTitles' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.jobTitles') })
</script>

<template>
  <SettingsOrgList kind="job_titles" />
</template>
