<!--
  Form builder (FRONTEND-SPEC §6, PROGRESS F7). Palette | canvas | inspector on large screens;
  below that the canvas with palette / inspector in slide-overs (tablet) or bottom drawers (phone)
  behind a floating bar. Header, saving and publishing come from <FormsBuilderFrame>.
-->
<script setup lang="ts">
import { publishIssues } from '#shared/utils/forms/build'

definePageMeta({ breadcrumb: 'builder.crumb' })

const { t } = useI18n()
const route = useRoute()
const session = useBuilderSession(String(route.params.id))
const { builder, form } = session
useHead({ title: () => (form.value ? `${form.value.name} · ${t('builder.crumb')}` : t('builder.crumb')) })

const issues = computed(() =>
  Object.fromEntries(
    (builder.schema.value ? publishIssues(builder.schema.value) : [])
      .filter(issue => issue.field_id)
      .map(issue => [issue.field_id!, t(`builder.issue.${issue.code}`)]),
  ),
)

const large = useMediaQuery('(min-width: 1024px)')
const tablet = useMediaQuery('(min-width: 768px)')
const paletteOpen = ref(false)
const inspectorOpen = ref(false)

defineShortcuts({
  meta_d: { handler: () => builder.duplicate(), usingInput: false },
  delete: () => builder.removeWithUndo(),
  backspace: () => builder.removeWithUndo(),
  alt_arrowup: () => builder.selected.value.length === 1 && builder.move(builder.selected.value[0]!, -1),
  alt_arrowdown: () => builder.selected.value.length === 1 && builder.move(builder.selected.value[0]!, 1),
  escape: () => (builder.selected.value = []),
})
</script>

<template>
  <FormsBuilderFrame :session="session" mode="build">
    <template #loading>
      <div class="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)_300px]" :aria-label="t('common.loading')">
        <USkeleton class="hidden h-[70vh] lg:block" />
        <USkeleton class="mx-auto h-[70vh] w-full max-w-3xl" />
        <USkeleton class="hidden h-[70vh] lg:block" />
      </div>
    </template>

    <div class="grid items-start gap-4 lg:grid-cols-[240px_minmax(0,1fr)_300px]">
      <UCard v-if="large" class="sticky top-0" :ui="{ body: 'p-3 sm:p-3 h-[calc(100dvh-11rem)]' }">
        <FormsBuilderPalette />
      </UCard>
      <div class="mb-20 min-w-0 rounded-xl bg-elevated/40 p-3 sm:p-5 lg:mb-0">
        <FormsBuilderCanvas :issues="issues" />
      </div>
      <UCard v-if="large" class="sticky top-0" :ui="{ body: 'p-4 sm:p-4 h-[calc(100dvh-11rem)]' }">
        <FormsBuilderInspector />
      </UCard>
    </div>

    <template v-if="!large">
      <!-- Below laptop width: palette and settings live in a floating bar at the bottom (thumb reach). -->
      <div class="pointer-events-none fixed inset-x-0 bottom-4 z-20 flex justify-center px-4">
        <div class="pointer-events-auto flex items-center gap-1 rounded-xl border border-default bg-default p-1 shadow-lg">
          <UButton icon="i-lucide-plus" :label="t('builder.palette.title')" color="neutral" @click="paletteOpen = true" />
          <UButton icon="i-lucide-sliders-horizontal" :label="t('builder.inspector.panel')" color="neutral" variant="ghost" @click="inspectorOpen = true" />
        </div>
      </div>
      <USlideover v-if="tablet" v-model:open="paletteOpen" side="left" :title="t('builder.palette.title')">
        <template #body><FormsBuilderPalette @added="paletteOpen = false" /></template>
      </USlideover>
      <UDrawer v-else v-model:open="paletteOpen" :title="t('builder.palette.title')" :ui="{ body: 'h-[60dvh]' }">
        <template #body><FormsBuilderPalette @added="paletteOpen = false" /></template>
      </UDrawer>
      <USlideover v-if="tablet" v-model:open="inspectorOpen" :title="t('builder.inspector.panel')">
        <template #body><FormsBuilderInspector /></template>
      </USlideover>
      <UDrawer v-else v-model:open="inspectorOpen" :title="t('builder.inspector.panel')" :ui="{ body: 'max-h-[75dvh] overflow-y-auto' }">
        <template #body><FormsBuilderInspector /></template>
      </UDrawer>
    </template>
  </FormsBuilderFrame>
</template>
