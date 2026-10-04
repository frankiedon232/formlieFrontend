<!--
  Designer → Page (F10, owner 2026-10-03): how the form's public link looks around the form,
  ten styles drawn as small pictures (the page-design miniature), the bar / panel colour, the
  website link and quick facts.
-->
<script setup lang="ts">
import { THEME_FRAMES, type ThemeFrame } from '#shared/utils/forms/theme'

const { t } = useI18n()
const d = useDesigner()
const theme = d.theme
const { profile } = useTenant()
const hasWebsite = computed(() => !!profile.value?.website)

const tones = computed(() =>
  (['light', 'dark', 'brand'] as const).map(value => ({
    value,
    label: t(`designer.frame.toneValue.${value}`),
  })),
)
const pick = (style: ThemeFrame) => d.set('frame', 'style', style)
</script>

<template>
  <div class="flex flex-col gap-4">
    <p class="text-xs text-muted">{{ t('designer.frame.hint') }}</p>

    <div class="grid grid-cols-2 gap-2" role="radiogroup" :aria-label="t('designer.group.frame')">
      <button
        v-for="style in THEME_FRAMES"
        :key="style"
        type="button"
        role="radio"
        :aria-checked="theme.frame.style === style"
        class="group flex flex-col gap-1.5 rounded-lg border p-1.5 text-start transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--ui-border-inverted)"
        :class="
          theme.frame.style === style
            ? 'border-inverted ring-1 ring-inverted'
            : 'border-default hover:border-accented'
        "
        @click="pick(style)"
      >
        <!-- Small picture of the style, in this form's tone and background (same as Resources → Landing pages) -->
        <span class="block overflow-hidden rounded-md border border-default" aria-hidden="true">
          <PageDesignsThumb :tokens="{ frame: { ...theme.frame, style }, page: theme.page }" />
        </span>
        <span
          class="px-0.5 text-xs font-medium"
          :class="theme.frame.style === style ? 'text-highlighted' : 'text-default'"
          >{{ t(`designer.frame.style.${style}`) }}</span
        >
      </button>
    </div>
    <p class="text-xs text-muted">{{ t(`designer.frame.styleHint.${theme.frame.style}`) }}</p>

    <FormsDesignerChoice
      v-if="!['minimal', 'centred', 'headline'].includes(theme.frame.style)"
      :label="t('designer.frame.tone')"
      :model-value="theme.frame.tone"
      :items="tones"
      @update:model-value="v => d.set('frame', 'tone', v as 'light' | 'dark' | 'brand')"
    />

    <USwitch
      :model-value="theme.frame.show_website"
      :label="t('designer.frame.showWebsite')"
      :description="hasWebsite ? t('designer.frame.showWebsiteHint') : t('designer.frame.noWebsite')"
      color="neutral"
      @update:model-value="v => d.set('frame', 'show_website', v)"
    />
    <USwitch
      v-if="theme.frame.style !== 'minimal'"
      :model-value="theme.frame.show_facts"
      :label="t('designer.frame.showFacts')"
      :description="t('designer.frame.showFactsHint')"
      color="neutral"
      @update:model-value="v => d.set('frame', 'show_facts', v)"
    />
  </div>
</template>
