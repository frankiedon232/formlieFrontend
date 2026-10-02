<!-- Ranking: put options in order. Drag to reorder, or use the ↑ / ↓ buttons (keyboard). -->
<script setup lang="ts">
import { VueDraggable } from 'vue-draggable-plus'
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()
const { t } = useI18n()

const labels = computed(
  () => new Map((props.field.options ?? []).map(option => [option.value, option.label])),
)
const order = ref<string[]>([])
watchEffect(() => {
  const saved = Array.isArray(value.value) ? (value.value as string[]) : []
  const all = (props.field.options ?? []).map(option => option.value)
  order.value = [...saved.filter(v => all.includes(v)), ...all.filter(v => !saved.includes(v))]
})
function commit() {
  value.value = [...order.value]
}
function move(index: number, direction: -1 | 1) {
  const to = index + direction
  if (to < 0 || to >= order.value.length) return
  order.value.splice(to, 0, ...order.value.splice(index, 1))
  commit()
}
const disabled = computed(() => props.mode === 'builder')
</script>

<template>
  <VueDraggable
    :id="id"
    v-model="order"
    tag="ol"
    :disabled="disabled"
    :animation="150"
    handle="[data-rank-handle]"
    class="flex flex-col gap-1.5"
    @end="commit"
  >
    <li
      v-for="(item, index) in order"
      :key="item"
      class="flex items-center gap-2 rounded-md border border-default bg-default px-2 py-1.5 text-sm"
    >
      <UIcon
        name="i-lucide-grip-vertical"
        class="size-4 shrink-0 cursor-grab text-muted"
        data-rank-handle
        aria-hidden="true"
      />
      <span class="w-5 text-center text-xs text-muted tabular-nums">{{ index + 1 }}</span>
      <span class="min-w-0 flex-1 truncate text-default">{{ labels.get(item) }}</span>
      <UButton
        icon="i-lucide-arrow-up"
        color="neutral"
        variant="ghost"
        size="xs"
        :disabled="disabled || index === 0"
        :aria-label="t('renderer.moveUp', { item: labels.get(item) })"
        @click="move(index, -1)"
      />
      <UButton
        icon="i-lucide-arrow-down"
        color="neutral"
        variant="ghost"
        size="xs"
        :disabled="disabled || index === order.length - 1"
        :aria-label="t('renderer.moveDown', { item: labels.get(item) })"
        @click="move(index, 1)"
      />
    </li>
  </VueDraggable>
</template>
