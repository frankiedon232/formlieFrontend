<!--
  Standard page frame: UDashboardPanel + shared top bar + page header (title, meta, actions).
  Every portal page renders inside <AppPanel id="…" :title="…">.
-->
<script setup lang="ts">
defineProps<{
  id: string
  title: string
  meta?: string
  metaIcon?: string
}>()
</script>

<template>
  <UDashboardPanel :id="id" :ui="{ body: 'gap-6 sm:gap-6 p-4 sm:p-6' }">
    <template #header>
      <AppNavbar />
    </template>

    <template #body>
      <AppPageHeader :title="title" :meta="meta" :meta-icon="metaIcon">
        <template v-if="$slots.meta" #meta>
          <slot name="meta" />
        </template>
        <template v-if="$slots.actions" #actions>
          <slot name="actions" />
        </template>
      </AppPageHeader>
      <slot />
    </template>
  </UDashboardPanel>
</template>
