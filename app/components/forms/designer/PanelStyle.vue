<!-- Designer groups: Typography · Colours (with contrast hints) · Inputs · Buttons. -->
<script setup lang="ts">
defineProps<{ group: 'typography' | 'colors' | 'inputs' | 'buttons' }>()
const { t } = useI18n()
const d = useDesigner()
const theme = d.theme

const options = (prefix: string, keys: readonly string[]) => keys.map(value => ({ value, label: t(`${prefix}.${value}`) }))
</script>

<template>
  <div class="flex flex-col gap-4">
    <template v-if="group === 'typography'">
      <UFormField :label="t('designer.font.label')">
        <USelect
          :model-value="theme.typography.font"
          :items="THEME_FONTS.map(value => ({ value, label: t(`designer.font.${value}`) }))"
          class="w-full"
          @update:model-value="v => d.set('typography', 'font', v as (typeof THEME_FONTS)[number])"
        />
      </UFormField>
      <FormsDesignerChoice :label="t('designer.textSize')" :model-value="theme.typography.size" :items="options('designer.size', ['sm', 'md', 'lg'])" @update:model-value="v => d.set('typography', 'size', v as 'sm' | 'md' | 'lg')" />
      <FormsDesignerChoice :label="t('designer.headingWeight')" :model-value="theme.typography.heading_weight" :items="options('designer.weight', ['medium', 'semibold', 'bold'])" @update:model-value="v => d.set('typography', 'heading_weight', v as 'medium' | 'semibold' | 'bold')" />
    </template>

    <template v-if="group === 'colors'">
      <FormsDesignerColorField :label="t('designer.color.primary')" :model-value="theme.colors.primary" :against="theme.container.bg" @update:model-value="v => d.set('colors', 'primary', v)" />
      <FormsDesignerColorField :label="t('designer.color.text')" :model-value="theme.colors.text" :against="theme.container.bg" @update:model-value="v => d.set('colors', 'text', v)" />
      <FormsDesignerColorField :label="t('designer.color.muted')" :model-value="theme.colors.muted" @update:model-value="v => d.set('colors', 'muted', v)" />
      <FormsDesignerColorField :label="t('designer.color.inputBg')" :model-value="theme.colors.input_bg" @update:model-value="v => d.set('colors', 'input_bg', v)" />
      <FormsDesignerColorField :label="t('designer.color.inputBorder')" :model-value="theme.colors.input_border" @update:model-value="v => d.set('colors', 'input_border', v)" />
      <FormsDesignerColorField :label="t('designer.color.error')" :model-value="theme.colors.error" @update:model-value="v => d.set('colors', 'error', v)" />
    </template>

    <template v-if="group === 'inputs'">
      <FormsDesignerChoice :label="t('designer.inputStyle')" :model-value="theme.inputs.style" :items="options('designer.style', ['outline', 'soft', 'underline'])" @update:model-value="v => d.set('inputs', 'style', v as 'outline' | 'soft' | 'underline')" />
      <FormsDesignerChoice :label="t('designer.size.label')" :model-value="theme.inputs.size" :items="options('designer.size', ['sm', 'md', 'lg'])" @update:model-value="v => d.set('inputs', 'size', v as 'sm' | 'md' | 'lg')" />
      <FormsDesignerChoice :label="t('designer.corners')" :model-value="theme.inputs.radius" :items="options('designer.size', ['none', 'sm', 'md', 'lg', 'full'])" @update:model-value="v => d.set('inputs', 'radius', v as 'none' | 'sm' | 'md' | 'lg' | 'full')" />
    </template>

    <template v-if="group === 'buttons'">
      <FormsDesignerChoice :label="t('designer.buttonStyle')" :model-value="theme.buttons.variant" :items="options('designer.style', ['solid', 'outline', 'soft'])" @update:model-value="v => d.set('buttons', 'variant', v as 'solid' | 'outline' | 'soft')" />
      <FormsDesignerChoice :label="t('designer.corners')" :model-value="theme.buttons.radius" :items="options('designer.size', ['none', 'sm', 'md', 'lg', 'full'])" @update:model-value="v => d.set('buttons', 'radius', v as 'none' | 'sm' | 'md' | 'lg' | 'full')" />
      <USwitch :model-value="theme.buttons.full_width" :label="t('designer.fullWidth')" color="neutral" @update:model-value="v => d.set('buttons', 'full_width', v)" />
    </template>
  </div>
</template>
