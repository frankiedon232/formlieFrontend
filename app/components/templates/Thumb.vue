<!--
  Template thumbnail (F9): a miniature of the form page in the template's own design, page
  background, card or side panel, header band, the first real questions and the button, so the
  gallery reads like a catalogue. Decorative (aria-hidden); the card carries the text.
-->
<script setup lang="ts">
import { fillBackground, pageBackground, readableOn, resolveTheme } from '#shared/utils/forms/theme'

/** card: gallery · compact: pickers · tile: card thumbnails (16:9, the form fills it) · mini: table rows (shapes only). */
const props = defineProps<{
  theme: Record<string, unknown>
  title: string
  labels: string[]
  compact?: boolean
  tile?: boolean
  mini?: boolean
}>()

const th = computed(() => resolveTheme(props.theme))
const background = computed(() => pageBackground(th.value))
const panel = computed(() => (th.value.layout === 'split' ? th.value.split : null))
const colourPanel = computed(() => !!panel.value && panel.value.panel !== 'image')
const band = computed(() =>
  !colourPanel.value && th.value.header.band !== 'none' && th.value.header.band !== 'accent'
    ? th.value.header
    : null,
)
const accent = computed(() =>
  !colourPanel.value && th.value.header.band === 'accent' ? th.value.header.band_bg : null,
)
const footerBar = computed(() => th.value.footer.enabled && th.value.footer.style === 'band')
const RADIUS: Record<string, string> = {
  none: '0',
  sm: '3px',
  md: '5px',
  lg: '8px',
  xl: '12px',
  full: '999px',
}
const INPUT_RADIUS = computed(() => RADIUS[th.value.inputs.radius] ?? '4px')
const centred = computed(() => th.value.header.align === 'center')
const shown = computed(() => props.labels.slice(0, props.mini || props.compact || props.tile ? 2 : 3))
</script>

<template>
  <div
    class="flex w-full overflow-hidden"
    :class="[
      mini ? 'h-10' : compact || tile ? 'aspect-[16/9]' : 'aspect-[16/10]',
      th.layout === 'full' ? '' : mini ? 'p-1' : tile ? 'px-2 pt-1.5' : compact ? 'p-2' : 'p-3',
    ]"
    :style="{ background }"
    aria-hidden="true"
  >
    <div
      class="mx-auto flex h-full w-full overflow-hidden"
      :class="[
        th.layout === 'full' || mini ? '' : tile ? (panel ? 'max-w-[94%]' : 'max-w-[86%]') : panel ? 'max-w-[78%]' : 'max-w-[62%]',
        tile && th.layout !== 'full' ? 'rounded-b-none!' : '',
        panel?.side === 'end' ? 'flex-row-reverse' : '',
      ]"
      :style="{
        background: th.layout === 'plain' ? 'transparent' : th.container.bg,
        borderRadius: mini ? '2px' : RADIUS[th.container.radius],
        boxShadow:
          th.layout === 'plain' || th.container.shadow === 'none' ? undefined : '0 2px 8px rgb(0 0 0 / 0.08)',
        fontFamily:
          th.typography.font === 'serif'
            ? 'Georgia, serif'
            : th.typography.font === 'mono'
              ? 'monospace'
              : undefined,
      }"
    >
      <!-- Side panel (colour / gradient carries the title) -->
      <div
        v-if="panel"
        class="flex w-2/5 shrink-0 flex-col justify-center p-2"
        :style="{
          background: colourPanel ? fillBackground(panel.panel, panel.bg, panel.bg_to, 160) : th.colors.muted,
          opacity: colourPanel ? 1 : 0.35,
        }"
      >
        <span
          v-if="colourPanel && !mini"
          class="line-clamp-3 text-[9px] leading-tight font-semibold"
          :style="{ color: readableOn(panel.bg) }"
          >{{ title }}</span
        >
      </div>

      <div class="flex min-w-0 flex-1 flex-col">
        <div
          v-if="band"
          class="shrink-0"
          :class="[mini ? 'h-1.5' : 'px-2.5 py-1.5', centred ? 'text-center' : '']"
          :style="{ background: fillBackground(band.band, band.band_bg, band.band_to) }"
        >
          <span
            v-if="!mini"
            class="line-clamp-1 text-[9px] font-semibold"
            :style="{ color: readableOn(band.band_bg) }"
            >{{ title }}</span
          >
        </div>

        <div
          class="flex min-h-0 flex-1 flex-col"
          :class="mini ? 'gap-0.5 px-1 py-0.5' : 'gap-1.5 px-2.5 py-2'"
          :style="{ color: th.colors.text }"
        >
          <span
            v-if="!band && !colourPanel && !mini"
            class="line-clamp-1 text-[9px] font-semibold"
            :class="[centred ? 'text-center' : '', accent ? 'rounded-sm border-s-2 px-1 py-0.5' : '']"
            :style="
              accent
                ? {
                    borderInlineStartColor: accent,
                    background: `color-mix(in oklab, ${accent} 8%, transparent)`,
                  }
                : undefined
            "
            >{{ title }}</span
          >
          <div v-for="label in shown" :key="label" class="flex flex-col gap-0.5">
            <span v-if="!mini" class="line-clamp-1 text-[7px] leading-tight opacity-80">{{ label }}</span>
            <span
              class="block w-full"
              :class="mini ? 'h-1' : 'h-2.5'"
              :style="{
                background: th.inputs.style === 'soft' ? th.colors.input_border : th.colors.input_bg,
                border: th.inputs.style === 'underline' ? 'none' : `1px solid ${th.colors.input_border}`,
                borderBottom: `1px solid ${th.colors.input_border}`,
                borderRadius: th.inputs.style === 'underline' ? '0' : INPUT_RADIUS,
              }"
            />
          </div>
          <span
            class="mt-auto shrink-0"
            :class="[mini ? 'h-1' : 'h-2.5', th.buttons.full_width ? 'w-full' : 'w-1/3 self-end']"
            :style="{
              background: th.buttons.variant === 'solid' ? th.colors.primary : 'transparent',
              border: `1px solid ${th.colors.primary}`,
              borderRadius: RADIUS[th.buttons.radius],
            }"
          />
        </div>
        <span
          v-if="footerBar && th.layout !== 'plain'"
          class="h-1.5 w-full shrink-0"
          :style="{ background: th.footer.bg }"
        />
      </div>
    </div>
  </div>
</template>
