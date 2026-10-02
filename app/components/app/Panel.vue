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

const { t } = useI18n()
const { busy } = useActivity()
// In-page sweeping bar under the header while the page navigates or loads (CLAUDE.md rule 5).
// A short delay keeps very fast requests from flashing it.
const showBar = refDebounced(busy, 150)
const visible = computed(() => busy.value && showBar.value)
</script>

<template>
  <UDashboardPanel :id="id" :ui="{ body: 'gap-6 sm:gap-6 p-4 sm:p-6' }">
    <template #header>
      <div class="relative">
        <AppNavbar :title="title" :subtitle="subtitle" :subtitle-icon="subtitleIcon">
          <template v-if="$slots.actions" #actions>
            <slot name="actions" />
          </template>
        </AppNavbar>
        <!-- Sits on the header's bottom edge: takes no space, stays visible while scrolling. -->
        <div class="pointer-events-none absolute inset-x-0 -bottom-px z-10 h-0.5" aria-hidden="true">
          <UProgress
            v-if="visible"
            animation="carousel"
            color="neutral"
            size="xs"
            :ui="{ root: 'gap-0', base: 'rounded-none bg-transparent', indicator: 'rounded-none' }"
          />
        </div>
        <span v-if="visible" class="sr-only" role="status">{{ t('common.loading') }}</span>
      </div>
    </template>

    <template #body>
      <slot />
    </template>

    <template #footer>
      <AppFooter />
    </template>
  </UDashboardPanel>
</template>
