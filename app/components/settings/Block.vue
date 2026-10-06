<!--
  One block of a Settings page (F14): the heading and a line of why on the left, the fields on the
  right (stacked on small screens). Blocks share the page's width so every page lines up the same.
-->
<script setup lang="ts">
defineProps<{ title: string; description?: string; icon?: string }>()
</script>

<template>
  <section class="grid gap-4 border-b border-default pb-6 last:border-b-0 last:pb-0 xl:grid-cols-[15rem_minmax(0,1fr)] xl:gap-10">
    <div class="flex min-w-0 flex-col gap-1">
      <h2 class="flex items-center gap-2 text-sm font-semibold text-highlighted">
        <UIcon v-if="icon" :name="icon" class="size-4 shrink-0 text-muted" />{{ title }}
      </h2>
      <p v-if="description" class="text-xs text-muted">{{ description }}</p>
    </div>
    <div class="flex min-w-0 flex-col gap-4">
      <slot />
    </div>
  </section>
</template>
