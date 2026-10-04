<!--
  Status overview as thin lines (docs/design 084447 "Task Status Overview"): about 48 thin bars
  shared out by each part's share, grouped and coloured per part, the group's share on top; a
  group can be a button (e.g. filter the list). Every group is named in the legend beside it.
-->
<script setup lang="ts">
const props = withDefaults(defineProps<{ parts: { key: string; label: string; count: number; color: string }[]; selected?: string | null; total?: number }>(), { selected: null, total: 48 })
const emit = defineEmits<{ pick: [key: string] }>()
const { percent, number } = useFormat()

const sum = computed(() => props.parts.reduce((s, part) => s + part.count, 0))
const groups = computed(() =>
  props.parts.map(part => {
    const share = sum.value ? part.count / sum.value : 0
    return { ...part, share, lines: part.count ? Math.max(1, Math.round(share * props.total)) : 0 }
  }),
)
</script>

<template>
  <div class="flex h-full items-end gap-2" role="list">
    <button
      v-for="group in groups.filter(item => item.lines)"
      :key="group.key"
      type="button"
      role="listitem"
      class="flex h-full min-w-0 flex-col justify-end gap-1.5 rounded-sm text-start transition-opacity focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--ui-border-inverted)"
      :class="selected && selected !== group.key ? 'opacity-30' : ''"
      :style="{ flexGrow: group.lines }"
      :aria-label="`${group.label}: ${number(group.count)} (${percent(group.share)})`"
      :aria-pressed="selected === group.key"
      @click="emit('pick', group.key)"
    >
      <span class="flex items-center gap-1 text-[11px] font-medium text-highlighted tabular-nums">
        <span class="size-1.5 rounded-[2px]" :class="group.color" />{{ percent(group.share) }}
      </span>
      <span class="flex h-full max-h-24 min-h-12 items-end gap-[3px]">
        <span v-for="n in group.lines" :key="n" class="w-[3px] shrink-0 rounded-full" :class="group.color" :style="{ height: n === 1 ? '100%' : `${78 + ((n * 37) % 17)}%` }" />
      </span>
    </button>
  </div>
</template>
