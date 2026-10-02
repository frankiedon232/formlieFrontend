<!-- Placeholder until F5 (forms list). -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.forms' })
const { t } = useI18n()
useHead({ title: () => t('nav.forms') })
</script>

<template>
  <AppPanel id="forms">
    <UEmpty
      icon="i-lucide-file-text"
      :title="t('placeholder.title')"
      :description="t('forms.description')"
      class="my-auto"
    />
  </AppPanel>
</template>
