<!-- One timeline row (design "Work Timeline"): square marker + dotted line, date, bold title, actions on the end. -->
<script setup lang="ts">
defineProps<{
  title: string
  when: string
  icon: string
  meta?: string
  summary?: string | null
  current?: boolean
  selected?: boolean
  last?: boolean
}>()
</script>

<template>
  <li class="relative flex gap-3 pb-5 last:pb-0">
    <div class="flex flex-col items-center">
      <span
        class="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md border"
        :class="current || selected ? 'border-inverted bg-inverted text-inverted' : 'border-default bg-default text-muted'"
      >
        <UIcon :name="icon" class="size-3.5" />
      </span>
      <span v-if="!last" class="mt-1 w-px flex-1 border-s border-dashed border-default" aria-hidden="true" />
    </div>
    <div class="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-start">
      <div class="min-w-0 flex-1">
        <p class="text-xs text-muted">{{ when }}</p>
        <p class="flex flex-wrap items-center gap-2 text-sm font-semibold text-highlighted">
          {{ title }}
          <slot name="badges" />
        </p>
        <p v-if="summary" class="mt-0.5 text-sm text-default">{{ summary }}</p>
        <p v-if="meta" class="mt-0.5 text-xs text-muted">{{ meta }}</p>
      </div>
      <div class="flex shrink-0 flex-wrap items-center gap-1.5">
        <slot />
      </div>
    </div>
  </li>
</template>
