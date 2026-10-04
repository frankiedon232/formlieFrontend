<!--
  Slim stacked bar with a legend (F11 review status): segments 2px apart, each with its colour,
  label, count and share in the legend; a legend item can be a button (e.g. filter the list).
  Colour never works alone: every segment is named in the legend.
-->
<script setup lang="ts">
const props = defineProps<{ parts: { key: string; label: string; count: number; color: string }[]; selected?: string | null; clickable?: boolean }>()
const emit = defineEmits<{ pick: [key: string] }>()
const { number, percent } = useFormat()
const total = computed(() => props.parts.reduce((sum, part) => sum + part.count, 0))
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex h-2 gap-0.5 overflow-hidden rounded-full bg-elevated" role="presentation">
      <div
        v-for="part in parts.filter(item => item.count)"
        :key="part.key"
        class="h-full first:rounded-s-full last:rounded-e-full transition-[width,opacity] duration-500"
        :class="[part.color, selected && selected !== part.key ? 'opacity-30' : '']"
        :style="{ width: `${(part.count / Math.max(1, total)) * 100}%` }"
      />
    </div>
    <ul class="flex flex-col gap-1">
      <li v-for="part in parts" :key="part.key">
        <component
          :is="clickable ? 'button' : 'div'"
          :type="clickable ? 'button' : undefined"
          class="flex w-full items-center gap-2 rounded-md text-start text-sm"
          :class="[clickable ? '-mx-1.5 px-1.5 py-1 hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)' : '', selected === part.key ? 'bg-elevated' : '']"
          :aria-pressed="clickable ? selected === part.key : undefined"
          @click="clickable && emit('pick', part.key)"
        >
          <span class="size-2.5 shrink-0 rounded-[3px]" :class="part.color" aria-hidden="true" />
          <span class="min-w-0 flex-1 truncate text-default">{{ part.label }}</span>
          <span class="text-xs text-muted tabular-nums">{{ number(part.count) }}</span>
          <span class="w-9 text-end text-xs font-medium text-highlighted tabular-nums">{{ percent(total ? part.count / total : 0) }}</span>
        </component>
      </li>
    </ul>
  </div>
</template>
