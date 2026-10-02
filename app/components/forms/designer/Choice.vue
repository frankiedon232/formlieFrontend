<!-- A labelled segmented control (design style) for one designer token. -->
<script setup lang="ts">
defineProps<{
  label: string
  modelValue: string
  items: { value: string; label: string; icon?: string }[]
  description?: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const ui = { ...SEGMENTED_UI, trigger: `${SEGMENTED_UI.trigger} flex-1 px-1.5`, label: 'truncate' }
</script>

<template>
  <UFormField :label="label" :description="description">
    <UTabs
      :model-value="modelValue"
      :items="items"
      :content="false"
      color="neutral"
      size="xs"
      :ui="ui"
      class="w-full"
      :aria-label="label"
      @update:model-value="v => emit('update:modelValue', String(v))"
    />
  </UFormField>
</template>
