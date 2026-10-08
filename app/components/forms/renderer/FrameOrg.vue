<!-- The organisation on a public form page: its logo (or initials on the brand colour) and name; with `form`, the form's name as a small line under it (owner 2026-10-08: the name belongs to the page, not the form body). -->
<script setup lang="ts">
defineProps<{
  org: { name: string; logo: string | null }
  initials: string
  accent: string
  onAccent: string
  /** On the brand hero: the initials chip turns light. */
  inverse?: boolean
  /** The form's name (theme "Show the form name"), for frames without a hero title. */
  form?: string | null
}>()
</script>

<template>
  <div class="flex min-w-0 items-center gap-3">
    <img
      v-if="org.logo"
      :src="org.logo"
      :alt="org.name"
      class="h-8 max-w-36 shrink-0 object-contain @xl:h-9"
    >
    <span
      v-else
      class="flex size-9 shrink-0 items-center justify-center rounded-lg text-sm font-semibold"
      :style="
        inverse
          ? { background: 'rgb(255 255 255 / 0.16)', color: 'currentColor' }
          : { background: accent, color: onAccent }
      "
      aria-hidden="true"
    >
      {{ initials }}
    </span>
    <span class="flex min-w-0 flex-col">
      <span class="truncate text-base leading-tight font-semibold tracking-tight">{{ org.name }}</span>
      <h1 v-if="form" class="truncate text-xs leading-tight font-normal opacity-75">{{ form }}</h1>
    </span>
  </div>
</template>
