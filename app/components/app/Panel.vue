<!--
  Standard page frame: UDashboardPanel + header bar (title, crumbs, subtitle, page actions) +
  clear content area + footer. Every portal page renders inside <AppPanel id="…" :title="…">
  and puts its buttons in #actions (secondary = outline, primary = solid).
-->
<script setup lang="ts">
defineProps<{
  id: string
  title: string
  subtitle?: string
  subtitleIcon?: string
}>()
</script>

<template>
  <UDashboardPanel :id="id" :ui="{ body: 'gap-6 sm:gap-6 p-4 sm:p-6' }">
    <template #header>
      <AppNavbar :title="title" :subtitle="subtitle" :subtitle-icon="subtitleIcon">
        <template v-if="$slots.actions" #actions>
          <slot name="actions" />
        </template>
      </AppNavbar>
    </template>

    <template #body>
      <slot />
    </template>

    <template #footer>
      <AppFooter />
    </template>
  </UDashboardPanel>
</template>
