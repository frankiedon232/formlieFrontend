<!-- Settings → Departments (F14 M2): the workspace's departments, with the people in them. -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'settings.nav.departments' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.departments') })
</script>

<template>
  <SettingsOrgList kind="departments" />
</template>
