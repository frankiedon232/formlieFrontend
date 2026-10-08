<!--
  Form builder (FRONTEND-SPEC §6, PROGRESS F7). Palette | canvas | inspector on large screens;
  below that the canvas with palette / inspector in slide-overs (tablet) or bottom drawers (phone)
  behind a floating bar. Header, saving and publishing come from <FormsBuilderFrame>.
  Both side panes collapse to a slim bar for a wider canvas (owner 2026-10-08; open by default,
  remembered in this browser); selecting a field opens the settings pane again.
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
// Side panes fill the height left under the page header, or under the slim bar in full screen.
const paneHeight = computed(() => (session.fullscreen.value ? 'h-[calc(100dvh-5.5rem)]' : 'h-[calc(100dvh-11rem)]'))
const paletteOpen = ref(false)
const inspectorOpen = ref(false)
// Large screens: the side panes, open unless collapsed (a display preference, kept in this browser)
const { fields: paletteShown, settings: inspectorShown } = useBuilderPanes()
watch(() => builder.selected.value.join(), ids => ids && (inspectorShown.value = true))
const columns = computed(() => GRID[`${paletteShown.value ? 'p' : '-'}${inspectorShown.value ? 'i' : '-'}`])
const GRID: Record<string, string> = {
  pi: 'lg:grid-cols-[240px_minmax(0,1fr)_300px]',
  'p-': 'lg:grid-cols-[240px_minmax(0,1fr)]',
  '-i': 'lg:grid-cols-[minmax(0,1fr)_300px]',
  '--': 'lg:grid-cols-1',
}
// The page fills the height left beside the panes and grows with its content
const canvasHeight = computed(() => (session.fullscreen.value ? 'min-h-[calc(100dvh-10rem)]' : 'min-h-[calc(100dvh-15.5rem)]'))
/** "Add field" from the canvas: the drawer / slide-over below laptop width, else the palette search. */
async function showFieldList() {
  if (!large.value) return void (paletteOpen.value = true)
  paletteShown.value = true
  await nextTick()
  document.querySelector<HTMLInputElement>('#builder-palette input')?.focus()
}

defineShortcuts({
  meta_d: { handler: () => builder.duplicate(), usingInput: false },
  delete: () => builder.removeWithUndo(),
  backspace: () => builder.removeWithUndo(),
  alt_arrowup: () => builder.selected.value.length === 1 && builder.move(builder.selected.value[0]!, -1),
  alt_arrowdown: () => builder.selected.value.length === 1 && builder.move(builder.selected.value[0]!, 1),
  escape: () => {
    // Esc: first clears the selection, then leaves full screen.
    if (builder.selected.value.length) builder.selected.value = []
    else if (session.fullscreen.value) void session.toggleFullscreen(false)
  },
})
</script>

<template>
  <FormsBuilderFrame :session="session" mode="build">
    <template #loading>
      <div class="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)_300px]" :aria-label="t('common.loading')">
        <USkeleton class="hidden h-[70vh] lg:block" />
        <USkeleton class="h-[70vh] w-full" />
        <USkeleton class="hidden h-[70vh] lg:block" />
      </div>
    </template>

    <div class="grid items-start gap-4" :class="columns">
      <template v-if="large">
        <UCard v-if="paletteShown" class="sticky top-0" :ui="{ body: `p-3 sm:p-3 ${paneHeight}` }">
          <FormsBuilderPalette id="builder-palette" />
        </UCard>
      </template>
      <div class="min-w-0 rounded-xl bg-elevated/40 p-2 sm:p-3">
        <FormsBuilderCanvas :issues="issues" :min-height="canvasHeight" @add-field="showFieldList" />
      </div>
      <template v-if="large">
        <UCard v-if="inspectorShown" class="sticky top-0" :ui="{ body: `p-4 sm:p-4 ${paneHeight}` }">
          <FormsBuilderInspector />
        </UCard>
      </template>
    </div>

    <template v-if="!large">
      <!-- Below laptop width: field list and settings in a bar that sticks to the bottom of the
           content (thumb reach), never over the footer. -->
      <div class="pointer-events-none sticky bottom-3 z-20 mt-3 flex justify-center">
        <div class="pointer-events-auto flex items-center gap-1 rounded-xl border border-default bg-default p-1 shadow-lg">
          <UButton icon="i-lucide-plus" :label="t('builder.palette.title')" color="neutral" @click="paletteOpen = true" />
          <UButton
            icon="i-lucide-sliders-horizontal"
            :label="t('builder.inspector.panel')"
            color="neutral"
            variant="ghost"
            @click="inspectorOpen = true"
          />
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
