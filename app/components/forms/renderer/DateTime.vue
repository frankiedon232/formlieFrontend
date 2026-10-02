<!-- Date, time, date-time and date range — native pickers (best on phones), Nuxt UI inputs. -->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()
const { t } = useI18n()

const TYPES: Record<string, string> = { date: 'date', time: 'time', datetime: 'datetime-local' }
const ICONS: Record<string, string> = {
  date: 'i-lucide-calendar',
  time: 'i-lucide-clock',
  datetime: 'i-lucide-calendar-clock',
}

const single = computed({
  get: () => (typeof value.value === 'string' ? value.value : ''),
  set: next => (value.value = next),
})
const range = computed(() =>
  value.value && typeof value.value === 'object' ? (value.value as { from?: string; to?: string }) : {},
)
const setRange = (part: 'from' | 'to', next: string) => (value.value = { ...range.value, [part]: next })
const readonly = computed(() => props.mode === 'builder')
</script>

<template>
  <div v-if="field.type === 'date_range'" class="grid gap-2 sm:grid-cols-2">
    <UInput
      :id="id"
      type="date"
      :model-value="range.from ?? ''"
      :aria-label="t('renderer.from')"
      :readonly="readonly"
      icon="i-lucide-calendar"
      class="w-full"
      @update:model-value="v => setRange('from', String(v))"
    />
    <UInput
      type="date"
      :model-value="range.to ?? ''"
      :aria-label="t('renderer.to')"
      :min="range.from"
      :readonly="readonly"
      icon="i-lucide-calendar"
      class="w-full"
      @update:model-value="v => setRange('to', String(v))"
    />
  </div>
  <UInput
    v-else
    :id="id"
    v-model="single"
    :type="TYPES[field.type]"
    :required="field.required"
    :readonly="readonly"
    :icon="ICONS[field.type]"
    class="w-full"
  />
</template>
