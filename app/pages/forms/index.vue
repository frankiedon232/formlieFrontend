<!-- Placeholder until F5 (forms list, DataView). Header actions follow docs/design. -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.forms' })
const { t } = useI18n()
useHead({ title: () => t('nav.forms') })
</script>

<template>
  <AppPanel id="forms" :title="t('nav.forms')" :meta="t('forms.description')" meta-icon="i-lucide-refresh-cw">
    <template #actions>
      <UButton
        icon="i-lucide-upload"
        :label="t('forms.import')"
        color="neutral"
        variant="outline"
        to="/forms/new"
      />
      <UButton icon="i-lucide-plus" :label="t('nav.newForm')" color="neutral" to="/forms/new" />
    </template>

    <UEmpty
      icon="i-lucide-file-text"
      :title="t('placeholder.title')"
      :description="t('placeholder.description')"
      variant="outline"
      class="flex-1"
    />
  </AppPanel>
</template>
