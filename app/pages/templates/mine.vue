<!--
  Your templates (owner, 2026-10-03): the workspace's own templates, saved from forms or
  duplicated from Formalie's, kept apart from Formalie's catalogue.
-->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.templatesMine' })
const { t } = useI18n()
useHead({ title: () => t('nav.templatesMine') })
const counts = useNavCounts()
</script>

<template>
  <AppPanel id="templates-mine" :title="t('nav.templatesMine')" :subtitle="t('templates.mine.subtitle')" subtitle-icon="i-lucide-bookmark">
    <template #actions>
      <UButton :label="t('nav.templatesAll')" icon="i-lucide-shapes" color="neutral" variant="outline" to="/templates" />
      <UButton :label="t('templates.blank')" icon="i-lucide-file" color="neutral" to="/forms/new" />
    </template>
    <TemplatesList id="templates-mine" source="workspace" @changed="counts.refresh(true)" />
  </AppPanel>
</template>
