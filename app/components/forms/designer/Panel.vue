<!--
  Designer controls (FRONTEND-SPEC §7), every part a collapsible group (owner 2026-10-04: the
  themes collapse like the rest, a little space under each open group): Starting points · Your
  themes · Page designs (Resources → Pages) · Page (the frame around the form on its link) · Layout · Background · Form container · Typography · Colours · Inputs · Buttons · Header ·
  Footer · Thank-you page. "Reset" goes back to the workspace default.
-->
<script setup lang="ts">
import type { AccordionItem } from '@nuxt/ui'

/** standalone: the theme editor (no "Your themes", you are editing one). */
const props = defineProps<{ standalone?: boolean }>()
const { t } = useI18n()
const d = useDesigner()
const confirm = useConfirm()

const groups = computed<AccordionItem[]>(() => [
  { value: 'starting', label: t('designer.startingPoints'), icon: 'i-lucide-sparkles', slot: 'starting' },
  ...(props.standalone ? [] : [{ value: 'themes', label: t('themes.yours'), icon: 'i-lucide-swatch-book', slot: 'themes' }]),
  { value: 'pages', label: t('pages.designerGroup'), icon: 'i-lucide-panels-top-left', slot: 'pages' },
  // The page around the form on its link (F10), first of the controls, because it's what people see first.
  { value: 'frame', label: t('designer.group.frame'), icon: 'i-lucide-app-window', slot: 'frame' },
  { value: 'layout', label: t('designer.group.layout'), icon: 'i-lucide-layout-template', slot: 'layout' },
  { value: 'background', label: t('designer.group.background'), icon: 'i-lucide-paint-bucket', slot: 'background' },
  { value: 'container', label: t('designer.group.container'), icon: 'i-lucide-square-dashed', slot: 'container' },
  { value: 'typography', label: t('designer.group.typography'), icon: 'i-lucide-type', slot: 'typography' },
  { value: 'colors', label: t('designer.group.colors'), icon: 'i-lucide-palette', slot: 'colors' },
  { value: 'inputs', label: t('designer.group.inputs'), icon: 'i-lucide-text-cursor-input', slot: 'inputs' },
  { value: 'buttons', label: t('designer.group.buttons'), icon: 'i-lucide-mouse-pointer-click', slot: 'buttons' },
  { value: 'header', label: t('designer.group.header'), icon: 'i-lucide-panel-top', slot: 'header' },
  { value: 'footer', label: t('designer.group.footer'), icon: 'i-lucide-panel-bottom', slot: 'footer' },
  { value: 'thank_you', label: t('designer.group.thankYou'), icon: 'i-lucide-party-popper', slot: 'thank_you' },
])
const open = ref<string[]>(['starting'])

async function reset() {
  if (await confirm({ title: t('designer.resetTitle'), description: t('designer.resetDesc'), confirmLabel: t('designer.reset') })) d.reset()
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <UAccordion v-model="open" type="multiple" :items="groups" :ui="{ trigger: 'text-sm font-medium', body: 'pb-6' }">
      <template #starting>
        <div class="flex flex-col gap-2">
          <FormsDesignerPresets />
          <div class="flex items-center justify-between gap-2">
            <p class="text-xs text-muted">{{ d.customised.value ? '' : t('designer.usingDefault') }}</p>
            <UButton v-if="d.customised.value" :label="t('designer.reset')" icon="i-lucide-rotate-ccw" color="neutral" variant="link" size="xs" class="px-0" @click="reset" />
          </div>
        </div>
      </template>
      <template #themes><FormsDesignerSavedThemes /></template>
      <template #pages><FormsDesignerPageDesigns /></template>
      <template #frame><FormsDesignerPanelFrame /></template>
      <template #layout><FormsDesignerPanelLayout group="layout" /></template>
      <template #background><FormsDesignerPanelLayout group="background" /></template>
      <template #container><FormsDesignerPanelLayout group="container" /></template>
      <template #typography><FormsDesignerPanelStyle group="typography" /></template>
      <template #colors><FormsDesignerPanelStyle group="colors" /></template>
      <template #inputs><FormsDesignerPanelStyle group="inputs" /></template>
      <template #buttons><FormsDesignerPanelStyle group="buttons" /></template>
      <template #header><FormsDesignerPanelContent group="header" /></template>
      <template #footer><FormsDesignerPanelContent group="footer" /></template>
      <template #thank_you><FormsDesignerPanelContent group="thank_you" /></template>
    </UAccordion>
  </div>
</template>
