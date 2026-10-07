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
  /** Colour for the subtitle icon (e.g. a folder's colour): a class and / or an inline style. */
  subtitleIconClass?: string
  subtitleIconStyle?: Record<string, string>
  /** Busy headers (form workspace): search shows as an icon button only. */
  compactSearch?: boolean
}>()

const { t } = useI18n()
const { busy } = useActivity()
// In-page sweeping bar under the header while the page navigates or loads (CLAUDE.md rule 5).
// A short delay keeps very fast requests from flashing it.
const showBar = refDebounced(busy, 150)
// Settings → Appearance: density, a centred content column (by padding, so the scrollbar stays at the edge), footer
const look = useAppearance().current
const bodyUi = computed(() => {
  const space = look.value.density === 'compact' ? 'gap-4 sm:gap-4 p-3 sm:p-4' : 'gap-6 sm:gap-6 p-4 sm:p-6'
  return look.value.content_width === 'centred' ? `${space} sm:px-[max(1.5rem,calc((100%-80rem)/2))]` : space
})
const visible = computed(() => busy.value && showBar.value)
</script>

<template>
  <UDashboardPanel :id="id" :ui="{ body: bodyUi }">
    <template #header>
      <div class="relative">
        <AppNavbar :title="title" :subtitle="subtitle" :subtitle-icon="subtitleIcon" :subtitle-icon-class="subtitleIconClass" :subtitle-icon-style="subtitleIconStyle" :compact-search="compactSearch">
          <template v-if="$slots.title" #title>
            <slot name="title" />
          </template>
          <template v-if="$slots.meta" #meta>
            <slot name="meta" />
          </template>
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

    <template v-if="look.footer" #footer>
      <AppFooter />
    </template>
  </UDashboardPanel>
</template>
