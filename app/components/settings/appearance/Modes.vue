<!--
  Settings → Appearance → Light and dark (leftovers L3, owner 2026-10-10): the mode people get until they pick
  one themselves (their own choice always wins), and optionally other colours in dark mode: accent, greys and
  background, picked like the light ones. Changes go to the page's draft (`change`), which the page saves.
-->
<script setup lang="ts">
import type { AppearanceSettings } from '#shared/types/appearance'

const props = defineProps<{
  draft: AppearanceSettings
  primaries: { value: string; label: string; class?: string; style?: Record<string, string> }[]
  neutrals: { value: string; label: string; class?: string }[]
}>()
const emit = defineEmits<{ change: [patch: Partial<AppearanceSettings>] }>()
const { t } = useI18n()

const modes = computed(() =>
  (['system', 'light', 'dark'] as const).map(value => ({ value, label: t(`settings.appearance.mode.${value}`), icon: { system: 'i-lucide-monitor', light: 'i-lucide-sun', dark: 'i-lucide-moon' }[value] })),
)
const backgrounds = computed(() => (['plain', 'tinted'] as const).map(value => ({ value, label: t(`settings.appearance.bg.${value}`) })))
function setMode(value: AppearanceSettings['default_mode']) {
  emit('change', { default_mode: value })
}
/** Turning dark colours on starts from the light ones, so nothing jumps. */
function setOwn(on: boolean) {
  emit('change', { dark: on ? { primary: props.draft.primary, neutral: props.draft.neutral, background: props.draft.background } : null })
}
function setDark<K extends keyof NonNullable<AppearanceSettings['dark']>>(key: K, value: NonNullable<AppearanceSettings['dark']>[K]) {
  if (props.draft.dark) emit('change', { dark: { ...props.draft.dark, [key]: value } })
}
</script>

<template>
  <SettingsBlock :title="t('settings.appearance.modes')" :description="t('settings.appearance.modesHint')" icon="i-lucide-sun-moon">
    <UFormField :label="t('settings.appearance.defaultMode')" :help="t('settings.appearance.defaultModeHelp')">
      <UTabs :model-value="draft.default_mode" :items="modes" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="w-fit max-w-full overflow-x-auto" @update:model-value="value => setMode(value as AppearanceSettings['default_mode'])" />
    </UFormField>
    <USwitch :model-value="!!draft.dark" :label="t('settings.appearance.darkOwn')" :description="t('settings.appearance.darkOwnHint')" color="neutral" @update:model-value="value => setOwn(!!value)" />
    <div v-if="draft.dark" class="flex flex-col gap-4 rounded-lg border border-default p-3 sm:p-4">
      <UFormField :label="t('settings.appearance.darkPrimary')">
        <SettingsAppearanceSwatches :model-value="draft.dark.primary" :items="primaries" :label="t('settings.appearance.darkPrimary')" @update:model-value="value => setDark('primary', value as AppearanceSettings['primary'])" />
      </UFormField>
      <UFormField :label="t('settings.appearance.darkNeutrals')">
        <SettingsAppearanceSwatches :model-value="draft.dark.neutral" :items="neutrals" :label="t('settings.appearance.darkNeutrals')" @update:model-value="value => setDark('neutral', value as AppearanceSettings['neutral'])" />
      </UFormField>
      <UFormField :label="t('settings.appearance.darkBackground')">
        <UTabs :model-value="draft.dark.background" :items="backgrounds" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="w-fit" @update:model-value="value => setDark('background', value as AppearanceSettings['background'])" />
      </UFormField>
    </div>
  </SettingsBlock>
</template>
