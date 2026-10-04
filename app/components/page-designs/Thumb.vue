<!--
  Page design miniature (Resources → Landing pages and the designer's style picker): the page around a form
  on its public link, drawn with shapes in a fixed 16:9 frame so every picture is the same size.
  The page background, the frame style (branded · spotlight · side · minimal · banner · centred ·
  headline · corporate · compact · floating) in its tone and the workspace's brand colour, and a
  small form card where the form sits. Decorative (aria-hidden).
-->
<script setup lang="ts">
import type { PageDesignTokens } from '#shared/utils/forms/page-design'
import { pageBackground, readableOn, resolveTheme } from '#shared/utils/forms/theme'

const props = defineProps<{ tokens: PageDesignTokens }>()
const branding = useWorkspaceBranding()
const theme = computed(() => resolveTheme({ frame: props.tokens.frame, page: props.tokens.page }, branding.value))
const style = computed(() => theme.value.frame.style)
const primary = computed(() => theme.value.colors.primary)
/** Bar / panel / band surface for the chosen tone (plain colour for bars, gradient for big areas). */
const surface = computed(() => {
  const tone = theme.value.frame.tone
  if (tone === 'dark') return { background: '#0a0a0a', color: '#fafafa' }
  if (tone === 'brand') return { background: `linear-gradient(135deg, ${primary.value}, color-mix(in oklab, ${primary.value} 62%, #000))`, color: readableOn(primary.value) }
  return { background: '#ffffff', color: '#18181b' }
})
const ink = computed(() => surface.value.color)
const bar = (width: string, opacity = 0.85, color = ink.value) => ({ background: color, width, opacity })
/** Styles whose top is a plain bar. */
const BARS = ['branded', 'corporate', 'compact']
</script>

<template>
  <div class="relative flex aspect-[16/9] w-full flex-col overflow-hidden" :style="{ background: pageBackground(theme) }" aria-hidden="true">
    <!-- Top: bar · hero · band · floating pill -->
    <div v-if="BARS.includes(style)" class="flex shrink-0 flex-col shadow-xs" :style="surface">
      <span v-if="style === 'corporate' && theme.frame.tone !== 'brand'" class="h-[2px]" :style="{ background: primary }" />
      <span class="flex items-center gap-1 px-[6%]" :class="style === 'compact' ? 'h-[11%] min-h-2.5' : 'h-[15%] min-h-3.5'">
        <span class="size-1.5 rounded-[2px]" :style="{ background: ink, opacity: 0.85 }" />
        <span class="h-[3px] rounded-full" :style="bar('16%')" />
        <span v-if="style === 'compact'" class="h-[2.5px] rounded-full" :style="bar('22%', 0.5)" />
        <span v-if="tokens.frame.show_website" class="ms-auto h-[3px] rounded-full" :style="bar('11%', 0.5)" />
      </span>
    </div>
    <div v-else-if="style === 'floating'" class="flex shrink-0 justify-center px-[8%] pt-[3%]">
      <span class="flex h-3 w-full items-center gap-1 rounded-full px-[3%] shadow-sm" :style="surface">
        <span class="size-1.5 rounded-full" :style="{ background: ink, opacity: 0.85 }" />
        <span class="h-[3px] w-[18%] rounded-full" :style="{ background: ink, opacity: 0.85 }" />
        <span v-if="tokens.frame.show_website" class="ms-auto h-[3px] w-[12%] rounded-full" :style="{ background: ink, opacity: 0.5 }" />
      </span>
    </div>
    <div v-else-if="style === 'spotlight' || style === 'banner'" class="flex h-[44%] shrink-0 flex-col justify-center gap-1" :class="style === 'banner' ? 'items-start px-[7%]' : 'items-center px-[10%]'" :style="surface">
      <span v-if="style === 'banner'" class="mb-0.5 size-1.5 rounded-[2px]" :style="{ background: ink, opacity: 0.85 }" />
      <span class="h-[4px] rounded-full" :style="bar(style === 'banner' ? '42%' : '38%')" />
      <span class="h-[2.5px] rounded-full" :style="bar(style === 'banner' ? '58%' : '52%', 0.55)" />
      <span v-if="tokens.frame.show_facts" class="mt-0.5 flex gap-1">
        <span v-for="n in 3" :key="n" class="h-[2.5px] w-3 rounded-full" :style="{ background: ink, opacity: 0.4 }" />
      </span>
    </div>
    <div v-else-if="style === 'centred'" class="flex shrink-0 flex-col items-center gap-0.5 pt-[5%]">
      <span class="size-2 rounded-[3px]" :style="{ background: primary }" />
      <span class="h-[3px] w-[16%] rounded-full bg-zinc-700/70" />
      <span v-if="tokens.frame.show_facts" class="flex gap-1 pt-0.5"><span v-for="n in 3" :key="n" class="h-[2px] w-2.5 rounded-full bg-zinc-500/50" /></span>
    </div>
    <div v-else-if="style === 'headline'" class="flex h-[13%] shrink-0 items-center gap-1 px-[6%]">
      <span class="size-1.5 rounded-[2px]" :style="{ background: primary }" />
      <span class="h-[3px] w-[16%] rounded-full bg-zinc-700/70" />
    </div>

    <!-- Middle: side panel or headline column, and the form card -->
    <div class="flex min-h-0 flex-1" :class="style === 'side' || style === 'headline' ? 'flex-row' : 'flex-col'">
      <div v-if="style === 'side'" class="flex w-[34%] shrink-0 flex-col justify-center gap-1 px-[4%]" :style="surface">
        <span class="size-1.5 rounded-[2px]" :style="{ background: ink, opacity: 0.85 }" />
        <span class="h-[3.5px] rounded-full" :style="bar('80%')" />
        <span class="h-[2.5px] rounded-full" :style="bar('60%', 0.55)" />
      </div>
      <div v-else-if="style === 'headline'" class="flex w-[40%] shrink-0 flex-col justify-center gap-1 ps-[6%]">
        <span class="h-[2px] w-[22%] rounded-full" :style="{ background: primary }" />
        <span class="h-[5px] w-[90%] rounded-full bg-zinc-800/80" />
        <span class="h-[5px] w-[70%] rounded-full bg-zinc-800/80" />
        <span class="h-[2.5px] w-[80%] rounded-full bg-zinc-500/50" />
      </div>
      <div
        class="flex min-h-0 flex-1 justify-center"
        :class="[
          style === 'spotlight' ? '-mt-[9%] items-start px-[8%]' : 'items-center',
          style === 'headline' ? 'px-[5%]' : 'px-[8%]',
          style === 'minimal' || style === 'centred' ? 'py-[6%]' : 'py-[4%]',
        ]"
      >
        <div class="flex h-full max-h-[86%] w-full flex-col gap-[6%] rounded-[3px] bg-white p-[4%] shadow-sm" :class="style === 'headline' ? 'max-w-[92%]' : 'max-w-[62%]'">
          <span class="h-[3px] w-1/2 rounded-full bg-zinc-800/80" />
          <span class="h-[5px] w-full rounded-[1.5px] border border-zinc-300" />
          <span class="h-[5px] w-full rounded-[1.5px] border border-zinc-300" />
          <span class="mt-auto h-[5px] w-1/4 self-end rounded-[1.5px]" :style="{ background: primary }" />
        </div>
      </div>
    </div>

    <!-- Bottom: footer band (corporate) or the slim secured line -->
    <div v-if="style === 'corporate'" class="flex h-[12%] shrink-0 items-center gap-1 px-[6%]" :style="surface">
      <span class="size-1.5 rounded-[2px]" :style="{ background: ink, opacity: 0.85 }" />
      <span class="h-[2.5px] w-[14%] rounded-full" :style="{ background: ink, opacity: 0.6 }" />
      <span class="ms-auto h-[2.5px] w-[12%] rounded-full" :style="{ background: ink, opacity: 0.5 }" />
    </div>
    <div v-else class="flex h-[7%] shrink-0 items-center justify-center">
      <span class="h-[2px] w-[14%] rounded-full bg-zinc-500/40" />
    </div>
  </div>
</template>
