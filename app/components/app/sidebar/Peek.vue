<!--
  Expanded menu shown over the page while the sidebar is collapsed (hover or keyboard focus).
  Fixed-positioned, so the page layout never shifts. While open, the rail behind it is `inert`,
  so Tab moves peek → page content and never lands on hidden rail items.
-->
<script setup lang="ts">
const { open, schedule, close } = useSidebarPeek()
const root = ref<HTMLElement | null>(null)

const focusables = () => [
  ...(root.value?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])') ?? []),
]

/** Called by the sidebar when keyboard focus enters the rail. */
function focusEdge(edge: 'first' | 'last') {
  nextTick(() => {
    const items = focusables()
    ;(edge === 'first' ? items[0] : items.at(-1))?.focus()
  })
}

watch(open, value => {
  document.getElementById(SIDEBAR_ELEMENT_ID)?.toggleAttribute('inert', value)
})

onKeyStroke('Escape', () => {
  // Esc closes the top-most layer first: an open dialog/menu wins over the peek.
  if (document.querySelector('[role="dialog"][data-state="open"], [role="menu"][data-state="open"]')) return
  close()
})

function onFocusOut(event: FocusEvent) {
  const next = event.relatedTarget as HTMLElement | null
  // Menus/popovers opened from inside the peek render in a portal; keep the peek open for them.
  if (next && (root.value?.contains(next) || next.closest('[data-reka-popper-content-wrapper]'))) return
  close()
}

onBeforeUnmount(() => document.getElementById(SIDEBAR_ELEMENT_ID)?.removeAttribute('inert'))

defineExpose({ focusEdge })
</script>

<template>
  <Transition
    enter-active-class="transition duration-150 ease-out motion-reduce:transition-none"
    enter-from-class="opacity-0 -translate-x-2 rtl:translate-x-2"
    leave-active-class="pointer-events-none transition duration-100 ease-in motion-reduce:transition-none"
    leave-to-class="opacity-0 -translate-x-2 rtl:translate-x-2"
  >
    <div
      v-if="open"
      ref="root"
      class="fixed inset-y-0 start-0 z-50 flex w-64 flex-col gap-4 border-e border-default bg-default p-4 shadow-xl"
      data-sidebar-peek
      @mouseenter="schedule(true)"
      @mouseleave="schedule(false)"
      @focusout="onFocusOut"
    >
      <AppSidebarBrand />
      <AppSidebarNav class="flex-1 overflow-y-auto" />
      <AppSidebarFooter />
    </div>
  </Transition>
</template>
