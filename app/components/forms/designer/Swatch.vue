<!-- Mini preview of a theme: page background, card, a title line, an input and the accent button. -->
<script setup lang="ts">
import type { FormTheme } from '#shared/utils/forms/theme'

const props = defineProps<{ theme: FormTheme; size?: 'sm' | 'md' }>()
const RADIUS: Record<string, string> = { none: '0', sm: '3px', md: '5px', lg: '7px', xl: '10px' }
const background = computed(() => pageBackground(props.theme))
</script>

<template>
  <span class="flex items-center justify-center rounded-md p-2" :class="size === 'sm' ? 'h-10 w-16' : 'h-16 w-full'" :style="{ background }" aria-hidden="true">
    <span
      class="flex h-full w-4/5 flex-col justify-center gap-1 px-2"
      :style="{
        background: theme.layout === 'plain' ? 'transparent' : theme.container.bg,
        borderRadius: RADIUS[theme.container.radius],
      }"
    >
      <span class="h-1 w-1/2 rounded-full" :style="{ background: theme.colors.text, opacity: 0.8 }" />
      <span class="h-2 w-full border" :style="{ background: theme.colors.input_bg, borderColor: theme.colors.input_border }" />
      <span class="h-2 w-1/3 self-end rounded-sm" :style="{ background: theme.colors.primary }" />
    </span>
  </span>
</template>
