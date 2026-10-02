<!--
  Standard page frame: UDashboardPanel + shared navbar + optional toolbar.
  Every portal page renders inside <AppPanel id="…">.
-->
<script setup lang="ts">
defineProps<{ id: string }>()
</script>

<template>
  <UDashboardPanel :id="id">
    <template #header>
      <AppNavbar />
      <UDashboardToolbar v-if="$slots.toolbar">
        <slot name="toolbar" />
      </UDashboardToolbar>
    </template>

    <template #body>
      <slot />
    </template>
  </UDashboardPanel>
</template>
