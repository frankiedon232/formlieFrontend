<!-- People → Roles & access (F22, last before payments): placeholder until custom roles and permissions are built. -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.peopleRoles' })
const { t } = useI18n()
useHead({ title: () => t('nav.peopleRoles') })
</script>

<template>
  <AppPanel id="people-roles" :title="t('nav.peopleRoles')">
    <AppComingSoon icon="i-lucide-shield" title-key="nav.peopleRoles" description-key="people.rolesSoon" :back="{ labelKey: 'nav.people', icon: 'i-lucide-users', to: '/people' }" />
  </AppPanel>
</template>
