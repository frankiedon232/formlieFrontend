<!--
  Designer group: Sections and blocks (owner 2026-10-08). How sections, dividers, paragraphs and
  images look in the form; each block keeps its own options (size, alignment, width) in the builder.
-->
<script setup lang="ts">
import type { FormTheme } from '#shared/utils/forms/theme'

type Blocks = FormTheme['blocks']
const { t } = useI18n()
const d = useDesigner()
const theme = d.theme

const options = (prefix: string, keys: readonly string[]) => keys.map(value => ({ value, label: t(`${prefix}.${value}`) }))
const set = <K extends keyof Blocks>(key: K, value: Blocks[K]) => d.set('blocks', key, value)
</script>

<template>
  <div class="flex flex-col gap-4">
    <p class="text-xs text-muted">{{ t('designer.blocks.hint') }}</p>

    <span class="text-xs font-medium text-muted uppercase">{{ t('builder.field.section') }}</span>
    <FormsDesignerChoice :label="t('designer.blocks.sectionStyle')" :model-value="theme.blocks.section" :items="options('designer.blocks.section', ['plain', 'underline', 'accent', 'band'])" @update:model-value="v => set('section', v as Blocks['section'])" />
    <FormsDesignerChoice :label="t('designer.blocks.headingColor')" :model-value="theme.blocks.section_color" :items="options('designer.blocks.color', ['text', 'primary'])" @update:model-value="v => set('section_color', v as Blocks['section_color'])" />
    <USwitch :model-value="theme.blocks.section_caps" :label="t('designer.blocks.caps')" color="neutral" @update:model-value="v => set('section_caps', v)" />

    <USeparator />
    <span class="text-xs font-medium text-muted uppercase">{{ t('builder.field.divider') }}</span>
    <FormsDesignerChoice :label="t('designer.blocks.dividerStyle')" :model-value="theme.blocks.divider" :items="options('designer.blocks.divider', ['line', 'accent', 'gradient', 'dots', 'space'])" @update:model-value="v => set('divider', v as Blocks['divider'])" />
    <FormsDesignerChoice v-if="theme.blocks.divider !== 'space'" :label="t('designer.blocks.weight')" :model-value="theme.blocks.divider_weight" :items="options('designer.blocks.weightOption', ['thin', 'thick'])" @update:model-value="v => set('divider_weight', v as Blocks['divider_weight'])" />

    <USeparator />
    <span class="text-xs font-medium text-muted uppercase">{{ t('builder.field.paragraph') }}</span>
    <FormsDesignerChoice :label="t('designer.blocks.paragraphStyle')" :model-value="theme.blocks.paragraph" :items="options('designer.blocks.paragraph', ['plain', 'muted', 'callout'])" @update:model-value="v => set('paragraph', v as Blocks['paragraph'])" />

    <USeparator />
    <span class="text-xs font-medium text-muted uppercase">{{ t('builder.field.image') }}</span>
    <FormsDesignerChoice :label="t('designer.corners')" :model-value="theme.blocks.image_radius" :items="options('designer.size', ['none', 'sm', 'md', 'lg', 'xl'])" @update:model-value="v => set('image_radius', v as Blocks['image_radius'])" />
    <USwitch :model-value="theme.blocks.image_shadow" :label="t('designer.blocks.shadow')" color="neutral" @update:model-value="v => set('image_shadow', v)" />
    <USwitch :model-value="theme.blocks.image_border" :label="t('designer.blocks.border')" color="neutral" @update:model-value="v => set('image_border', v)" />
  </div>
</template>
