<!-- Rating (stars), scale / NPS (numbered buttons with end labels) and slider. Keyboard: Tab + Enter / arrows. -->
<script setup lang="ts">
import { isLocked, type FormField } from '#shared/utils/forms/build'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()
const { t } = useI18n()

const p = computed(() => (props.field.props ?? {}) as Record<string, number | string | undefined>)
const current = computed(() => (typeof value.value === 'number' ? value.value : null))
const stars = computed(() => Array.from({ length: Number(p.value.max ?? 5) }, (_, i) => i + 1))
const steps = computed(() => {
  const min = Number(p.value.min ?? 0)
  const max = Number(p.value.max ?? 10)
  return Array.from({ length: Math.max(0, max - min + 1) }, (_, i) => min + i)
})
const slider = computed({
  get: () => current.value ?? Number(p.value.min ?? 0),
  set: next => (value.value = next),
})
// Read-only and disabled both block changes here (Nuxt UI choice controls have no read-only state).
const disabled = computed(() => isLocked(props.field))
</script>

<template>
  <div
    v-if="field.type === 'rating'"
    :id="id"
    class="flex flex-wrap gap-1"
    role="radiogroup"
    :aria-label="field.label"
  >
    <UButton
      v-for="n in stars"
      :key="n"
      role="radio"
      :aria-checked="current === n"
      :aria-label="t('renderer.stars', { n }, n)"
      icon="i-lucide-star"
      color="neutral"
      variant="ghost"
      size="lg"
      square
      :disabled="disabled"
      :class="current !== null && n <= current ? 'text-amber-500 [&_svg]:fill-current' : 'text-dimmed'"
      @click="value = n"
    />
  </div>

  <div v-else-if="field.type === 'scale'" :id="id" class="flex flex-col gap-1.5">
    <div class="flex flex-wrap gap-1.5" role="radiogroup" :aria-label="field.label">
      <UButton
        v-for="n in steps"
        :key="n"
        role="radio"
        :aria-checked="current === n"
        :label="String(n)"
        color="neutral"
        :variant="current === n ? 'solid' : 'outline'"
        size="sm"
        :disabled="disabled"
        class="min-w-9 justify-center tabular-nums"
        @click="value = n"
      />
    </div>
    <div v-if="p.min_label || p.max_label" class="flex justify-between gap-2 text-xs text-muted">
      <span>{{ p.min_label }}</span>
      <span>{{ p.max_label }}</span>
    </div>
  </div>

  <div v-else :id="id" class="flex items-center gap-3">
    <USlider
      v-model="slider"
      :min="Number(p.min ?? 0)"
      :max="Number(p.max ?? 100)"
      :step="Number(p.step ?? 1)"
      color="neutral"
      :disabled="disabled"
      :aria-label="field.label"
      class="flex-1"
    />
    <span class="w-12 text-end text-sm text-default tabular-nums">{{ slider }}</span>
  </div>
</template>
