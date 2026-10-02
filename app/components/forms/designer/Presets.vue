<!--
  Starting points: mini previews of each preset (background, card, accent, button). Choosing one
  replaces the design (one undo step). "Workspace default" follows the brand colour and logo.
-->
<script setup lang="ts">
const { t } = useI18n()
const designer = useDesigner()
const branding = useWorkspaceBranding()
const confirm = useConfirm()

const presets = computed(() =>
  THEME_PRESETS.map(preset => {
    const theme = applyPatch(resolveTheme(undefined, branding.value), preset.patch)
    return { ...preset, theme }
  }),
)

async function pick(patch: (typeof THEME_PRESETS)[number]['patch']) {
  if (designer.customised.value && !(await confirm({ title: t('designer.replaceTitle'), description: t('designer.replaceDesc'), confirmLabel: t('designer.replace') })))
    return
  designer.applyPreset(patch)
}
</script>

<template>
  <div class="grid grid-cols-2 gap-2">
    <button
      v-for="preset in presets"
      :key="preset.key"
      type="button"
      class="group/preset flex flex-col gap-1.5 rounded-lg border border-default p-1.5 text-start transition-colors hover:border-accented focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
      :aria-label="t('designer.applyPreset', { name: t(`designer.preset.${preset.key}`) })"
      @click="pick(preset.patch)"
    >
      <FormsDesignerSwatch :theme="preset.theme" />
      <span class="truncate px-0.5 text-xs font-medium text-highlighted">{{ t(`designer.preset.${preset.key}`) }}</span>
    </button>
  </div>
</template>
