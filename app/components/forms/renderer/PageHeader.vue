<!--
  Form page header content: logo, form name, intro text. On a coloured band or side panel the
  text switches to black or white, whichever reads better on that colour.
-->
<script setup lang="ts">
import type { FormTheme } from '#shared/utils/forms/theme'

const props = defineProps<{ theme: FormTheme; title: string; logo: string | null; on?: string | null }>()
const { t } = useI18n()
const WEIGHT: Record<string, string> = { medium: 'font-medium', semibold: 'font-semibold', bold: 'font-bold' }
const color = computed(() => (props.on ? readableOn(props.on) : null))
// Accent: a compact, quote-like block, coloured edge, soft tint, so the form keeps its full width.
const accent = computed(() => !props.on && props.theme.header.band === 'accent')
const accentStyle = computed(() =>
  accent.value
    ? {
        borderInlineStartColor: props.theme.header.band_bg,
        background: `color-mix(in oklab, ${props.theme.header.band_bg} 7%, transparent)`,
      }
    : undefined,
)
</script>

<template>
  <header
    class="flex flex-col gap-3"
    :class="[theme.header.align === 'center' ? 'items-center text-center' : 'items-start', accent ? 'rounded-lg border-s-4 px-4 py-3 sm:px-5 sm:py-4' : '']"
    :style="color ? { color } : accentStyle"
  >
    <img v-if="logo" :src="logo" :alt="t('renderer.page.logo')" class="max-h-12 w-auto max-w-48 object-contain" >
    <div v-if="theme.header.show_title || theme.header.subtitle" class="flex flex-col gap-1">
      <h1 v-if="theme.header.show_title" class="text-2xl" :class="[WEIGHT[theme.typography.heading_weight], color ? '' : 'text-highlighted']">
        {{ title }}
      </h1>
      <p v-if="theme.header.subtitle" class="whitespace-pre-line" :class="color ? 'opacity-80' : 'text-muted'">{{ theme.header.subtitle }}</p>
    </div>
  </header>
</template>
