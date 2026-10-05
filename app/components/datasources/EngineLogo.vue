<!-- A database engine's mark in an outlined tile (monochrome ink, like the design's icons). -->
<script setup lang="ts">
const props = withDefaults(defineProps<{ engine: string; size?: 'sm' | 'md' | 'lg' }>(), { size: 'md' })
const SIZES = { sm: 'size-8 rounded-md [&_.iconify]:size-4', md: 'size-10 rounded-lg [&_.iconify]:size-5', lg: 'size-16 rounded-2xl [&_.iconify]:size-8' }
</script>

<template>
  <span class="inline-flex shrink-0 items-center justify-center border border-default bg-default text-highlighted" :class="SIZES[props.size]" :title="engineName(engine)">
    <UIcon :name="engineIcon(engine)" :aria-label="engineName(engine)" />
  </span>
</template>
