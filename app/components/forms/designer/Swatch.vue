<!--
  Mini preview of a theme: page background, card (or side panel), header band, a title line,
  an input, the accent button and a footer bar — enough to tell the starting points apart.
-->
<script setup lang="ts">
import type { FormTheme } from '#shared/utils/forms/theme'

const props = defineProps<{ theme: FormTheme; size?: 'sm' | 'md' }>()
/** Saved themes may predate newer tokens — fill them from the defaults. */
const th = computed(() => resolveTheme(props.theme))
const RADIUS: Record<string, string> = { none: '0', sm: '3px', md: '5px', lg: '7px', xl: '10px' }
const background = computed(() => pageBackground(th.value))
const panel = computed(() => (th.value.layout === 'split' ? th.value.split : null))
const panelFill = computed(() =>
  !panel.value ? '' : panel.value.panel === 'image' ? th.value.colors.muted : fillBackground(panel.value.panel, panel.value.bg, panel.value.bg_to, 160),
)
const band = computed(() => (th.value.header.band !== 'none' && !(panel.value && panel.value.panel !== 'image') ? th.value.header : null))
const footerBar = computed(() => th.value.footer.enabled && th.value.footer.style === 'band')
</script>

<template>
  <span class="flex flex-col items-center justify-center rounded-md" :class="[size === 'sm' ? 'h-10 w-16 p-1.5' : 'h-16 w-full', th.layout === 'plain' && footerBar ? 'pt-2' : 'p-2']" :style="{ background }" aria-hidden="true">
    <span
      class="flex h-full w-4/5 overflow-hidden"
      :class="panel?.side === 'end' ? 'flex-row-reverse' : ''"
      :style="{
        background: th.layout === 'plain' ? 'transparent' : th.container.bg,
        borderRadius: RADIUS[th.container.radius],
      }"
    >
      <span v-if="panel" class="h-full w-2/5 shrink-0" :style="{ background: panelFill, opacity: panel.panel === 'image' ? 0.35 : 1 }" />
      <span class="flex min-w-0 flex-1 flex-col">
        <span v-if="band" class="h-2.5 w-full shrink-0" :style="{ background: fillBackground(band.band, band.band_bg, band.band_to) }" />
        <span class="flex flex-1 flex-col justify-center gap-1 px-2">
          <span v-if="!band" class="h-1 w-1/2 rounded-full" :style="{ background: th.colors.text, opacity: 0.8 }" />
          <span class="h-2 w-full border" :style="{ background: th.colors.input_bg, borderColor: th.colors.input_border }" />
          <span class="h-2 w-1/3 self-end rounded-sm" :style="{ background: th.colors.primary }" />
        </span>
        <span v-if="footerBar && th.layout !== 'plain'" class="h-1.5 w-full shrink-0" :style="{ background: th.footer.bg }" />
      </span>
    </span>
    <span v-if="footerBar && th.layout === 'plain'" class="mt-1 h-1.5 w-full shrink-0" :style="{ background: th.footer.bg }" />
  </span>
</template>
