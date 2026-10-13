<script setup lang="ts">
// The animated demo for one area of the product (feature pages, the features overview).
defineProps<{ name: DemoName }>()
</script>

<template>
  <DemoBuild v-if="name === 'build'" />
  <DemoDesign v-else-if="name === 'design'" />
  <DemoResponses v-else-if="name === 'responses'" />
  <DemoData v-else-if="name === 'data'" />
  <DemoApi v-else-if="name === 'api'" />
  <DemoDashboard v-else />
</template>
