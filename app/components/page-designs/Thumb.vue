<!--
  Page design miniature (Resources → Pages): the page around a form on its public link, drawn with
  shapes in a fixed 16:9 frame so every card's picture is the same size. The page background, the
  frame style (branded top bar · spotlight hero · side panel · minimal) in its tone and the
  workspace's brand colour, and a small form card where the form sits. Decorative (aria-hidden).
-->
<script setup lang="ts">
import type { PageDesignTokens } from '#shared/utils/forms/page-design'
import { pageBackground, readableOn, resolveTheme } from '#shared/utils/forms/theme'

const props = defineProps<{ tokens: PageDesignTokens }>()
const branding = useWorkspaceBranding()
const theme = computed(() => resolveTheme({ frame: props.tokens.frame, page: props.tokens.page }, branding.value))
const style = computed(() => theme.value.frame.style)
const primary = computed(() => theme.value.colors.primary)
/** The bar / panel / hero surface for the chosen tone. */
const surface = computed(() => {
  const tone = theme.value.frame.tone
  if (tone === 'dark') return { background: '#0a0a0a', color: '#fafafa' }
  if (tone === 'brand') return { background: `linear-gradient(135deg, ${primary.value}, color-mix(in oklab, ${primary.value} 62%, #000))`, color: readableOn(primary.value) }
  return { background: '#ffffff', color: '#18181b' }
})
const line = (color: string, width: string, opacity = 0.85) => ({ background: color, width, opacity })
</script>

<template>
  <div class="relative flex aspect-[16/9] w-full flex-col overflow-hidden" :style="{ background: pageBackground(theme) }" aria-hidden="true">
    <!-- Branded: a top bar with logo, name and website -->
    <div v-if="style === 'branded'" class="flex h-[16%] shrink-0 items-center gap-1 px-[6%] shadow-xs" :style="surface">
      <span class="size-1.5 rounded-[2px]" :style="{ background: surface.color, opacity: 0.85 }" />
      <span class="h-[3px] rounded-full" :style="line(surface.color, '18%')" />
      <span v-if="tokens.frame.show_website" class="ms-auto h-[3px] rounded-full" :style="line(surface.color, '12%', 0.5)" />
    </div>

    <!-- Spotlight: a tall hero with title and intro; the form card overlaps it -->
    <div v-else-if="style === 'spotlight'" class="flex h-[46%] shrink-0 flex-col justify-center gap-1 px-[10%]" :style="surface">
      <span class="h-[4px] rounded-full" :style="line(surface.color, '38%')" />
      <span class="h-[2.5px] rounded-full" :style="line(surface.color, '52%', 0.55)" />
      <span v-if="tokens.frame.show_facts" class="mt-0.5 flex gap-1">
        <span v-for="n in 3" :key="n" class="h-[2.5px] w-[9%] rounded-full" :style="{ background: surface.color, opacity: 0.4 }" />
      </span>
    </div>

    <div class="flex min-h-0 flex-1" :class="style === 'side' ? 'flex-row' : 'flex-col'">
      <!-- Side: a branded panel beside the form -->
      <div v-if="style === 'side'" class="flex w-[34%] shrink-0 flex-col justify-center gap-1 px-[4%]" :style="surface">
        <span class="size-1.5 rounded-[2px]" :style="{ background: surface.color, opacity: 0.85 }" />
        <span class="h-[3.5px] rounded-full" :style="line(surface.color, '80%')" />
        <span class="h-[2.5px] rounded-full" :style="line(surface.color, '60%', 0.55)" />
      </div>

      <!-- The form card -->
      <div class="flex min-h-0 flex-1 justify-center px-[8%]" :class="[style === 'spotlight' ? '-mt-[9%] items-start' : 'items-center', style === 'minimal' ? 'py-[7%]' : 'py-[5%]']">
        <div class="flex h-full max-h-[86%] w-full max-w-[62%] flex-col gap-[6%] rounded-[3px] bg-white p-[4%] shadow-sm">
          <span class="h-[3px] w-1/2 rounded-full bg-zinc-800/80" />
          <span class="h-[5px] w-full rounded-[1.5px] border border-zinc-300" />
          <span class="h-[5px] w-full rounded-[1.5px] border border-zinc-300" />
          <span class="mt-auto h-[5px] w-1/4 self-end rounded-[1.5px]" :style="{ background: primary }" />
        </div>
      </div>
    </div>

    <!-- Footer: secured by Formalie (and the organisation in branded / side) -->
    <div class="flex h-[7%] shrink-0 items-center justify-center gap-1">
      <span class="h-[2px] w-[14%] rounded-full bg-zinc-500/40" />
    </div>
  </div>
</template>
