<!--
  Your templates (owner, 2026-10-03): the workspace's own templates, saved from forms or
  duplicated from Formalie's, kept apart from Formalie's catalogue. Two chart cards on top (rule 21).
-->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.templatesMine' })
const { t } = useI18n()
useHead({ title: () => t('nav.templatesMine') })
const counts = useNavCounts()
const { insights, refresh } = useTemplateInsights()
/** A template was used, duplicated or deleted: sidebar counts and the top cards follow. */
function changed() {
  counts.refresh(true)
  refresh()
}
</script>

<template>
  <AppPanel
    id="templates-mine"
    :title="t('nav.templatesMine')"
    :subtitle="t('templates.mine.subtitle')"
    subtitle-icon="i-lucide-bookmark"
  >
    <template #actions>
      <UButton
        :label="t('nav.templatesAll')"
        icon="i-lucide-shapes"
        color="neutral"
        variant="outline"
        to="/templates"
      />
      <UButton :label="t('templates.blank')" icon="i-lucide-file" color="neutral" to="/forms/new" />
    </template>
    <div class="flex flex-col gap-4">
      <TemplatesOverview :insights="insights" />
      <TemplatesList
        id="templates-mine"
        source="workspace"
        :total="insights?.forms_total"
        @changed="changed"
      />
    </div>
  </AppPanel>
</template>
