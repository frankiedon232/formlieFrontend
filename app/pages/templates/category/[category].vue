<!--
  One of Formalie's template categories (owner, 2026-10-03): its templates in Grid / Table with
  search, features filter and sort (table / grid only, owner 2026-10-04).
  Unknown categories go back to the overview.
-->
<script setup lang="ts">
import { categoryOf } from '#shared/templates/categories'

definePageMeta({ breadcrumb: 'nav.templates' })
const { t } = useI18n()
const route = useRoute()
const counts = useNavCounts()
const { setLabel } = useBreadcrumbs()
const { insights, refresh } = useTemplateInsights()
/** A template was used or duplicated: sidebar counts and the top cards follow. */
function changed() {
  counts.refresh(true)
  refresh()
}

const key = computed(() => String(route.params.category ?? ''))
const category = computed(() => categoryOf(key.value))
const name = computed(() => (category.value ? t(`templates.categories.${key.value}`) : ''))
if (!category.value) await navigateTo('/templates', { replace: true })
watchEffect(() => name.value && setLabel(route.path, name.value))
useHead({ title: () => name.value || t('nav.templates') })
</script>

<template>
  <AppPanel
    v-if="category"
    :id="`templates-${key}`"
    :title="name"
    :subtitle="t('templates.categoryPage.subtitle')"
    :subtitle-icon="category.icon"
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
      <TemplatesList
        :id="`templates-${key}`"
        :key="key"
        source="system"
        :category="key"
        :total="insights?.forms_total"
        @changed="changed"
      />
    </div>
  </AppPanel>
</template>
