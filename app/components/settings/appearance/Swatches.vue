<!--
  Settings → Appearance (F14 M6): colour choices as round swatches (radio group): monochrome, the
  brand colour, palette colours; or the neutral palettes. Arrow keys move, the chosen one is ringed.
-->
<script setup lang="ts">
const model = defineModel<string>({ required: true })
defineProps<{ items: { value: string; label: string; class?: string; style?: Record<string, string> }[]; label: string }>()
</script>

<template>
  <div role="radiogroup" :aria-label="label" class="flex flex-wrap gap-2">
    <UTooltip v-for="item in items" :key="item.value" :text="item.label">
      <button
        type="button"
        role="radio"
        :aria-checked="model === item.value"
        :aria-label="item.label"
        class="flex size-9 items-center justify-center rounded-full border-2 transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--ui-border-inverted)"
        :class="model === item.value ? 'border-(--ui-border-inverted)' : 'border-transparent hover:border-(--ui-border-accented)'"
        @click="model = item.value"
      >
        <span class="size-6 rounded-full ring-1 ring-black/10 dark:ring-white/15" :class="item.class" :style="item.style" />
      </button>
    </UTooltip>
  </div>
</template>
