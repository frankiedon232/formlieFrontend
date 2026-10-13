<script setup lang="ts">
// The frame of an animated product demo: an app window like the real Formalie, light or dark with the site, with a
// soft glow behind it (docs/DESIGN.md). Decorative: the demos are hidden from screen readers.
defineProps<{ title: string; icon?: string }>()
</script>

<template>
  <div class="relative" aria-hidden="true">
    <div class="absolute -inset-6 rounded-[2rem] bg-violet-500/10 blur-2xl" />
    <div
      class="relative overflow-hidden rounded-2xl bg-default shadow-2xl shadow-black/10 ring-1 ring-default select-none"
    >
      <div class="flex items-center gap-3 border-b border-default bg-elevated/40 px-4 py-2.5">
        <span class="flex gap-1.5">
          <span class="size-2.5 rounded-full bg-accented" />
          <span class="size-2.5 rounded-full bg-accented" />
          <span class="size-2.5 rounded-full bg-accented" />
        </span>
        <span class="flex min-w-0 items-center gap-2 text-xs font-semibold text-highlighted">
          <UIcon v-if="icon" :name="icon" class="size-3.5 text-muted" />
          <span class="truncate">{{ title }}</span>
        </span>
        <span class="ms-auto flex items-center gap-2">
          <slot name="actions" />
        </span>
      </div>
      <div class="relative p-4 sm:p-5">
        <slot />
      </div>
    </div>
  </div>
</template>
