<!-- A database value as it is stored: NULL dimmed, JSON shortened, long text clipped (full value in the row panel). -->
<script setup lang="ts">
const props = defineProps<{ value: unknown; full?: boolean }>()
const shown = computed(() => {
  const value = props.value
  if (value === null || value === undefined) return null
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
})
const json = computed(() => {
  if (!props.full || shown.value === null) return null
  const text = shown.value.trim()
  if (!/^[[{]/.test(text)) return null
  try {
    return JSON.stringify(JSON.parse(text), null, 2)
  } catch {
    return null
  }
})
</script>

<template>
  <span v-if="shown === null" class="font-mono text-[11px] text-dimmed italic">NULL</span>
  <pre v-else-if="json" class="max-h-64 overflow-auto rounded-md bg-elevated px-2 py-1.5 font-mono text-[11px] whitespace-pre-wrap text-default" dir="ltr">{{ json }}</pre>
  <span v-else :class="full ? 'break-words whitespace-pre-wrap' : 'block max-w-64 truncate'" dir="auto">{{ shown }}</span>
</template>
