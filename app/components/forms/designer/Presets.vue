<!--
  Starting points: mini previews of each preset (background, card, accent, button). Choosing one
  replaces the design at once, no confirm (owner 2026-10-06: try freely; one undo step, the toast offers Undo).
  "Workspace default" follows the brand colour and logo.
-->
<script setup lang="ts">
const { t } = useI18n()
const designer = useDesigner()
const branding = useWorkspaceBranding()

const presets = computed(() =>
  THEME_PRESETS.map(preset => {
    const theme = applyPatch(resolveTheme(undefined, branding.value), preset.patch)
    return { ...preset, theme }
  }),
)

function pick(preset: (typeof THEME_PRESETS)[number]) {
  designer.applyPreset(preset.patch)
  designer.applied(t(`designer.preset.${preset.key}`))
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
      @click="pick(preset)"
    >
      <FormsDesignerSwatch :theme="preset.theme" />
      <span class="truncate px-0.5 text-xs font-medium text-highlighted">{{ t(`designer.preset.${preset.key}`) }}</span>
    </button>
  </div>
</template>
