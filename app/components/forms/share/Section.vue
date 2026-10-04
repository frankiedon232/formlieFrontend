<!-- A titled group on the Share tab (owner, 2026-10-04): "Answering the form" and "Your team". -->
<script setup lang="ts">
defineProps<{ icon: string; title: string; description: string }>()
</script>

<template>
  <div class="flex items-start gap-3 border-b border-default pb-2">
    <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-inverted text-inverted">
      <UIcon :name="icon" class="size-4" />
    </span>
    <div class="min-w-0">
      <h2 class="text-base font-semibold text-highlighted">{{ title }}</h2>
      <p class="text-xs text-muted">{{ description }}</p>
    </div>
  </div>
</template>
