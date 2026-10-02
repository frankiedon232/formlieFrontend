<script setup lang="ts">
const { t } = useI18n()
const { items } = useBreadcrumbs()
</script>

<template>
  <UBreadcrumb :items="items" :aria-label="t('navbar.breadcrumb')" :ui="{ root: 'min-w-0' }" />
</template>
