<!-- Designer groups: Layout (+ split image) · Background · Form container. -->
<script setup lang="ts">
defineProps<{ group: 'layout' | 'background' | 'container' }>()
const { t } = useI18n()
const d = useDesigner()
const theme = d.theme

const layouts = computed(() =>
  THEME_LAYOUTS.map(value => ({ value, label: t(`designer.layout.${value}`), icon: { card: 'i-lucide-square', plain: 'i-lucide-align-justify', split: 'i-lucide-columns-2', full: 'i-lucide-maximize' }[value] })),
)
const sizes = (keys: readonly string[]) => keys.map(value => ({ value, label: t(`designer.size.${value}`) }))
const bgTypes = computed(() => [
  { value: 'color', label: t('designer.bg.color') },
  { value: 'gradient', label: t('designer.bg.gradient') },
  { value: 'image', label: t('designer.bg.image') },
])
const sides = computed(() => [
  { value: 'start', label: t('designer.side.start') },
  { value: 'end', label: t('designer.side.end') },
])
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Layout -->
    <template v-if="group === 'layout'">
      <div class="grid grid-cols-2 gap-2" role="radiogroup" :aria-label="t('designer.group.layout')">
        <UButton
          v-for="item in layouts"
          :key="item.value"
          :icon="item.icon"
          :label="item.label"
          color="neutral"
          :variant="theme.layout === item.value ? 'solid' : 'outline'"
          size="sm"
          role="radio"
          :aria-checked="theme.layout === item.value"
          class="justify-start"
          @click="d.setLayout(item.value)"
        />
      </div>
      <p class="text-xs text-muted">{{ t(`designer.layoutHint.${theme.layout}`) }}</p>
      <template v-if="theme.layout === 'split'">
        <FormsDesignerImageField :label="t('designer.splitImage')" :model-value="theme.split.image" @update:model-value="v => d.set('split', 'image', v)" />
        <FormsDesignerChoice :label="t('designer.imageSide')" :model-value="theme.split.side" :items="sides" @update:model-value="v => d.set('split', 'side', v as 'start' | 'end')" />
      </template>
    </template>

    <!-- Background -->
    <template v-if="group === 'background'">
      <FormsDesignerChoice :label="t('designer.bg.type')" :model-value="theme.page.bg_type" :items="bgTypes" @update:model-value="v => d.set('page', 'bg_type', v as 'color' | 'gradient' | 'image')" />
      <FormsDesignerColorField :label="theme.page.bg_type === 'gradient' ? t('designer.bg.from') : t('designer.bg.color')" :model-value="theme.page.bg" @update:model-value="v => d.set('page', 'bg', v)" />
      <template v-if="theme.page.bg_type === 'gradient'">
        <FormsDesignerColorField :label="t('designer.bg.to')" :model-value="theme.page.bg_to" @update:model-value="v => d.set('page', 'bg_to', v)" />
        <UFormField :label="t('designer.bg.angle')" :hint="`${theme.page.gradient_angle}°`">
          <USlider :model-value="theme.page.gradient_angle" :min="0" :max="360" :step="15" color="neutral" @update:model-value="v => d.set('page', 'gradient_angle', Number(v))" />
        </UFormField>
      </template>
      <template v-if="theme.page.bg_type === 'image'">
        <FormsDesignerImageField :label="t('designer.bg.image')" :model-value="theme.page.bg_image" @update:model-value="v => d.set('page', 'bg_image', v)" />
        <UFormField :label="t('designer.bg.overlay')" :description="t('designer.bg.overlayHint')" :hint="`${theme.page.overlay}%`">
          <USlider :model-value="theme.page.overlay" :min="0" :max="80" :step="5" color="neutral" @update:model-value="v => d.set('page', 'overlay', Number(v))" />
        </UFormField>
      </template>
    </template>

    <!-- Form container -->
    <template v-if="group === 'container'">
      <FormsDesignerChoice :label="t('designer.container.width')" :model-value="theme.container.width" :items="sizes(['sm', 'md', 'lg', 'xl'])" @update:model-value="v => d.set('container', 'width', v as 'sm' | 'md' | 'lg' | 'xl')" />
      <FormsDesignerChoice :label="t('designer.container.padding')" :model-value="theme.container.padding" :items="sizes(['sm', 'md', 'lg'])" @update:model-value="v => d.set('container', 'padding', v as 'sm' | 'md' | 'lg')" />
      <template v-if="theme.layout === 'card' || theme.layout === 'split'">
        <FormsDesignerChoice :label="t('designer.container.radius')" :model-value="theme.container.radius" :items="sizes(['none', 'sm', 'md', 'lg', 'xl'])" @update:model-value="v => d.set('container', 'radius', v as 'none' | 'sm' | 'md' | 'lg' | 'xl')" />
        <FormsDesignerChoice :label="t('designer.container.shadow')" :model-value="theme.container.shadow" :items="sizes(['none', 'sm', 'md', 'lg'])" @update:model-value="v => d.set('container', 'shadow', v as 'none' | 'sm' | 'md' | 'lg')" />
        <USwitch :model-value="theme.container.border" :label="t('designer.container.border')" color="neutral" @update:model-value="v => d.set('container', 'border', v)" />
      </template>
      <FormsDesignerColorField v-if="theme.layout !== 'plain'" :label="t('designer.container.bg')" :model-value="theme.container.bg" @update:model-value="v => d.set('container', 'bg', v)" />
    </template>
  </div>
</template>
