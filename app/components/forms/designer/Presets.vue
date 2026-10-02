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
    return { ...preset, theme, background: pageBackground(theme) }
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
      <span class="flex h-16 items-center justify-center rounded-md p-2" :style="{ background: preset.background }" aria-hidden="true">
        <span
          class="flex h-full w-4/5 flex-col justify-center gap-1 px-2"
          :style="{
            background: preset.theme.layout === 'plain' ? 'transparent' : preset.theme.container.bg,
            borderRadius: { none: '0', sm: '3px', md: '5px', lg: '7px', xl: '10px' }[preset.theme.container.radius],
          }"
        >
          <span class="h-1 w-1/2 rounded-full" :style="{ background: preset.theme.colors.text, opacity: 0.8 }" />
          <span class="h-2 w-full border" :style="{ background: preset.theme.colors.input_bg, borderColor: preset.theme.colors.input_border }" />
          <span class="h-2 w-1/3 self-end rounded-sm" :style="{ background: preset.theme.colors.primary }" />
        </span>
      </span>
      <span class="truncate px-0.5 text-xs font-medium text-highlighted">{{ t(`designer.preset.${preset.key}`) }}</span>
    </button>
  </div>
</template>
