<!-- Dashboard shell: sidebar + page panel, command palette, shortcuts help, notifications. -->
<script setup lang="ts">
// The dashboard group uses its own storage key (template): bump it when sidebar size defaults change so saved sizes reset once.
const router = useRouter()
const route = useRoute()
const navCounts = useNavCounts()
// Sidebar badges: load now, then refresh on navigation when stale.
watch(
  () => route.path,
  () => navCounts.refresh(),
  { immediate: true },
)
const { destinations } = useNavigation()
const { shortcutsOpen } = useAppUi()
const peek = ref<{ focusEdge: (edge: 'first' | 'last') => void } | null>(null)
// The workspace's look of the portal (Settings → Appearance)
const appearance = useAppearance()
appearance.apply()
onMounted(() => void appearance.load())

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
  <UDashboardGroup unit="rem" storage-key="formalie-layout">
    <AppSidebar @peek-focus="edge => peek?.focusEdge(edge)" />
    <AppSidebarPeek ref="peek" />
    <slot />
    <AppSearch />
    <AppShortcutsModal />
    <AppNavbarNotifications />
    <AppConfirmDialog />
  </UDashboardGroup>
</template>
