<!--
  One slim horizontal bar with its label, count and share (F11 question summaries, channels): the
  label and numbers sit above a 6px track; the leading option can be emphasised.
-->
<script setup lang="ts">
const props = defineProps<{ label: string; count: number; total: number; strong?: boolean; icon?: string }>()
const { number, percent } = useFormat()
const share = computed(() => (props.total ? props.count / props.total : 0))
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <div class="flex items-baseline justify-between gap-3 text-sm">
      <span class="flex min-w-0 items-center gap-1.5 truncate" :class="strong ? 'font-medium text-highlighted' : 'text-default'">
        <UIcon v-if="icon" :name="icon" class="size-3.5 shrink-0 text-muted" />
        <span class="truncate">{{ label }}</span>
      </span>
      <span class="shrink-0 text-xs text-muted tabular-nums">
        {{ number(count) }} <span class="text-dimmed">·</span> <span class="font-medium text-highlighted">{{ percent(share) }}</span>
      </span>
    </div>
    <div class="h-1.5 overflow-hidden rounded-full bg-elevated" role="presentation">
      <div class="h-full rounded-full transition-[width] duration-500" :class="strong ? 'bg-inverted' : 'bg-inverted/45'" :style="{ width: `${Math.max(share * 100, count ? 1.5 : 0)}%` }" />
    </div>
  </div>
</template>
