<!--
  Menu column shown next to the rail, over the page, while the sidebar is collapsed.
  Fixed-positioned, so the page layout never shifts. Opened by keyboard focus → the sidebar is
  `inert` while open, so Tab moves peek → page content and never lands on hidden items.
-->
<script setup lang="ts">
const { open, mode, schedule, close } = useSidebarPeek()
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
  document.getElementById(SIDEBAR_ELEMENT_ID)?.toggleAttribute('inert', value && mode.value === 'focus')
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
  if (mode.value === 'focus') close()
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
      class="fixed inset-y-0 start-17 z-50 flex w-60 border-e border-default bg-default shadow-xl"
      data-sidebar-peek
      @mouseenter="schedule(true)"
      @mouseleave="schedule(false)"
      @focusout="onFocusOut"
    >
      <AppSidebarMenu />
    </div>
  </Transition>
</template>
