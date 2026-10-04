<!--
  Designer → Page (F10, owner 2026-10-03): how the form's public link looks around the form,
  four styles drawn as small pictures, the bar / panel colour, the website link and quick facts.
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
        <!-- Small picture of the style -->
        <span
          class="flex aspect-[4/3] w-full overflow-hidden rounded-md border border-default bg-muted"
          aria-hidden="true"
        >
          <span v-if="style === 'side'" class="flex w-full">
            <span class="flex w-2/5 flex-col justify-between bg-inverted p-1.5">
              <span class="h-1 w-6 rounded-full bg-(--ui-bg)/70" />
              <span class="flex flex-col gap-1"
                ><span class="h-1.5 w-10 rounded-full bg-(--ui-bg)" /><span
                  class="h-1 w-8 rounded-full bg-(--ui-bg)/60"
              /></span>
              <span class="h-1 w-5 rounded-full bg-(--ui-bg)/50" />
            </span>
            <span class="flex flex-1 items-center justify-center p-1.5"
              ><span class="flex h-4/5 w-full flex-col gap-1 rounded-sm bg-default p-1"
                ><span class="h-1 w-3/4 rounded-full bg-accented" /><span
                  class="h-1.5 w-full rounded-sm bg-elevated" /><span
                  class="h-1.5 w-full rounded-sm bg-elevated" /></span
            ></span>
          </span>
          <span v-else class="flex w-full flex-col">
            <span
              v-if="style !== 'minimal'"
              class="flex h-3 shrink-0 items-center justify-between px-1.5"
              :class="style === 'spotlight' ? 'bg-inverted' : 'border-b border-default bg-default'"
            >
              <span
                class="h-1 w-6 rounded-full"
                :class="style === 'spotlight' ? 'bg-(--ui-bg)/70' : 'bg-accented'"
              />
              <span
                class="h-1.5 w-4 rounded-full border"
                :class="style === 'spotlight' ? 'border-(--ui-bg)/60' : 'border-accented'"
              />
            </span>
            <span
              v-if="style === 'spotlight'"
              class="flex h-7 shrink-0 flex-col items-center justify-center gap-0.5 bg-inverted pb-2"
              ><span class="h-1.5 w-12 rounded-full bg-(--ui-bg)" /><span
                class="h-1 w-8 rounded-full bg-(--ui-bg)/60"
            /></span>
            <span class="flex flex-1 justify-center px-3" :class="style === 'spotlight' ? '-mt-3' : 'pt-1.5'">
              <span class="flex w-full flex-col gap-1 rounded-sm bg-default p-1 shadow-xs"
                ><span class="h-1 w-3/4 rounded-full bg-accented" /><span
                  class="h-1.5 w-full rounded-sm bg-elevated" /><span
                  class="h-1.5 w-full rounded-sm bg-elevated"
              /></span>
            </span>
            <span class="mt-auto h-1.5 shrink-0 border-t border-default" />
          </span>
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
      v-if="theme.frame.style !== 'minimal'"
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
