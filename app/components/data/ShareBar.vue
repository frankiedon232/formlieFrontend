<!--
  A share as a slim black bar with its percentage (locked list format, rule 21): table cells such as
  Reviewed on Responses or Share of use on Templates and Themes. `value` is 0 to 1.
-->
<script setup lang="ts">
const props = defineProps<{ value: number }>()
const { percent } = useFormat()
const width = computed(() => `${Math.min(1, Math.max(0, props.value)) * 100}%`)
</script>

<template>
  <div class="flex min-w-32 items-center gap-2">
    <div class="h-1.5 flex-1 overflow-hidden rounded-full bg-elevated" role="presentation">
      <div class="h-full rounded-full bg-inverted" :style="{ width }" />
    </div>
    <span class="w-9 text-end text-xs tabular-nums">{{ percent(value) }}</span>
  </div>
</template>
