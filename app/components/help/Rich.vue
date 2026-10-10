<!-- Help text with **bold** parts, rendered as text (never as HTML), F25. -->
<script setup lang="ts">
const props = defineProps<{ text: string }>()
const parts = computed(() => props.text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map(part => (part.startsWith('**') && part.endsWith('**') ? { bold: true, text: part.slice(2, -2) } : { bold: false, text: part })))
</script>

<template>
  <span><template v-for="(part, index) in parts" :key="index"><strong v-if="part.bold" class="font-semibold text-highlighted">{{ part.text }}</strong><template v-else>{{ part.text }}</template></template></span>
</template>
