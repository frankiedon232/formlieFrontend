<!-- Dashboard shell: sidebar + page panel, command palette, shortcuts help, notifications. -->
<script setup lang="ts">
const router = useRouter()
const { destinations } = useNavigation()
const { shortcutsOpen } = useAppUi()
const peek = ref<{ focusEdge: (edge: 'first' | 'last') => void } | null>(null)

// `?` opens the shortcuts help; `g` then a letter jumps to a section (see useNavigation).
const goTo = Object.fromEntries(
  destinations.value.filter(item => item.shortcut).map(item => [item.shortcut!, () => router.push(item.to)]),
)

defineShortcuts({
  'shift_?': () => {
    shortcutsOpen.value = true
  },
  '?': () => {
    shortcutsOpen.value = true
  },
  ...goTo,
})
</script>

<template>
  <UDashboardGroup unit="rem">
    <AppSidebar @peek-focus="edge => peek?.focusEdge(edge)" />
    <AppSidebarPeek ref="peek" />
    <slot />
    <AppSearch />
    <AppShortcutsModal />
    <AppNavbarNotifications />
  </UDashboardGroup>
</template>
