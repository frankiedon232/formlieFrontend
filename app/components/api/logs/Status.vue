<!-- An HTTP status as a small badge: green when it worked, amber for the caller's mistakes, red for ours. -->
<script setup lang="ts">
const props = defineProps<{ status: number; code?: string | null }>()
const color = computed(() => (props.status >= 500 ? 'error' : props.status >= 400 ? 'warning' : 'success'))
</script>

<template>
  <UBadge :label="String(status)" :color="color" variant="subtle" size="sm" class="rounded-md font-mono tabular-nums" :title="code ?? undefined" />
</template>
