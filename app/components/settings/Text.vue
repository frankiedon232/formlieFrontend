<!--
  A text input for an optional setting (F14): shows an empty box for null and gives null back for an
  empty box, so optional fields stay null when left blank. Every other attribute goes to UInput.
-->
<script setup lang="ts">
defineOptions({ inheritAttrs: false })
const model = defineModel<string | null>({ required: true })
const text = computed({
  get: () => model.value ?? '',
  set: (value: string | number) => (model.value = String(value) || null),
})
</script>

<template>
  <UInput v-model="text" v-bind="$attrs" />
</template>
