<!--
  Template page (F9): live preview in the template's design beside what's included, the formulas
  as snippets, usage and the latest forms made from it (slider + "View all"). Use → builder.
-->
<script setup lang="ts">
import type { TemplateDetail } from '#shared/types/templates'

definePageMeta({ breadcrumb: 'nav.templates' })
const { t } = useI18n()
const route = useRoute()
const templates = useTemplates()
const { setLabel } = useBreadcrumbs()
const { handle } = useErrorHandler()

const key = computed(() => String(route.params.key ?? ''))
const template = ref<TemplateDetail | null>(null)
const loading = ref(true)
const notFound = ref(false)
async function load() {
  loading.value = true
  notFound.value = false
  try {
    template.value = await templates.get(key.value)
    setLabel(route.path, template.value.name)
  } catch (error) {
    template.value = null
    notFound.value = true
    handle(error, { silent: true })
  } finally {
    loading.value = false
  }
}
watch(key, load, { immediate: true })
useHead({ title: () => template.value?.name ?? t('nav.templates') })

const useOpen = ref(false)
const { busy: duplicating, run } = useBusy()
async function duplicate() {
  if (!template.value) return
  const copy = await run(() => templates.duplicate(template.value!))
  if (copy) await navigateTo(`/templates/${copy.key}`)
}
</script>

<template>
  <AppPanel
    id="template"
    :title="template?.name ?? t('nav.templates')"
    :subtitle="
      template
        ? `${t(`templates.categories.${template.category}`)} · ${t('templates.minutes', { n: template.minutes })}`
        : undefined
    "
    :subtitle-icon="template?.icon"
  >
    <template v-if="template" #actions>
      <UButton
        :label="
          template.source === 'workspace'
            ? t('nav.templatesMine')
            : t(`templates.categories.${template.category}`)
        "
        :icon="template.source === 'workspace' ? 'i-lucide-bookmark' : 'i-lucide-shapes'"
        color="neutral"
        variant="ghost"
        :to="template.source === 'workspace' ? '/templates/mine' : `/templates/category/${template.category}`"
      />
      <UButton
        :label="t('templates.duplicate')"
        icon="i-lucide-copy"
        color="neutral"
        variant="outline"
        :loading="duplicating"
        @click="duplicate"
      />
      <UButton
        :label="t('templates.use')"
        icon="i-lucide-file-plus"
        color="neutral"
        @click="useOpen = true"
      />
    </template>

    <!-- Loading: mirrors preview + side panel -->
    <div v-if="loading" class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <USkeleton class="h-[70vh] min-h-96 w-full rounded-lg" />
      <div class="flex flex-col gap-3">
        <USkeleton class="h-48 w-full rounded-lg" />
        <USkeleton class="h-28 w-full rounded-lg" />
      </div>
    </div>

    <UEmpty
      v-else-if="notFound"
      icon="i-lucide-layout-template"
      :title="t('templates.notFound')"
      :description="t('templates.notFoundDesc')"
      :actions="[
        {
          label: t('templates.backToGallery'),
          icon: 'i-lucide-arrow-left',
          to: '/templates',
          color: 'neutral',
          variant: 'subtle',
        },
      ]"
      class="my-auto"
    />

    <template v-else-if="template">
      <p class="-mb-2 max-w-3xl text-sm text-muted">{{ template.description }}</p>
      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <TemplatesPreview :schema="template.schema" :title="template.name" />
        <TemplatesIncluded :template="template" @use="useOpen = true" />
      </div>

      <TemplatesUseModal v-model:open="useOpen" :template="template" />
    </template>
  </AppPanel>
</template>
