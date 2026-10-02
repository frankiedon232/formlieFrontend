<!--
  Page title block (docs/design): large title, small meta line,
  actions on the right (secondary = outline, primary = solid black). Stacks on phones.
-->
<script setup lang="ts">
const props = defineProps<{
  title: string
  /** Small line under the title, e.g. "Last sync: Just now". */
  meta?: string
  metaIcon?: string
}>()
</script>

<template>
  <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
    <div class="min-w-0">
      <h1 class="truncate text-2xl font-semibold tracking-tight text-highlighted">{{ props.title }}</h1>
      <p v-if="props.meta || $slots.meta" class="mt-1 flex items-center gap-1.5 text-sm text-muted">
        <UIcon v-if="props.metaIcon" :name="props.metaIcon" class="size-3.5" />
        <slot name="meta">{{ props.meta }}</slot>
      </p>
    </div>
    <div v-if="$slots.actions" class="flex shrink-0 flex-wrap items-center gap-2">
      <slot name="actions" />
    </div>
  </div>
</template>
