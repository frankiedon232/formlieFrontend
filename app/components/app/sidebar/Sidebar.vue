<!--
  Sidebar = rail + menu column (docs/design). Expanded ↔ collapsed (rail only) is remembered in a
  cookie by UDashboardGroup; `[` toggles. Collapsed + hover/keyboard focus on the rail's section
  icons → the menu column peeks over the page (AppSidebarPeek). Phones: slide-over drawer with both.
-->
<script setup lang="ts">
const emit = defineEmits<{ peekFocus: [edge: 'first' | 'last'] }>()
const { t } = useI18n()
const { open: peekOpen, mode, collapsed: sharedCollapsed, available, schedule, close } = useSidebarPeek()
const collapsed = ref(false)
const takeover = useSidebarTakeover()

watch(
  collapsed,
  value => {
    sharedCollapsed.value = value
    close()
  },
  { immediate: true },
)

const railNav = ref<HTMLElement | null>(null)
onMounted(() => {
  railNav.value = document.getElementById(RAIL_NAV_ID)
})
watch(collapsed, () => nextTick(() => (railNav.value = document.getElementById(RAIL_NAV_ID))))

useEventListener(railNav, 'mouseenter', () => schedule(true))
useEventListener(railNav, 'mouseleave', () => schedule(false))
useEventListener(railNav, 'focusin', (event: FocusEvent) => {
  if (!available.value || peekOpen.value) return
  if (!(event.target as HTMLElement).matches(':focus-visible')) return
  const from = event.relatedTarget as Node | null
  // Coming back with Shift+Tab from the page → land on the peek's last item.
  const fromAfter =
    !!from &&
    !!railNav.value &&
    !!(railNav.value.compareDocumentPosition(from) & Node.DOCUMENT_POSITION_FOLLOWING)
  mode.value = 'focus'
  peekOpen.value = true
  emit('peekFocus', fromAfter ? 'last' : 'first')
})

defineShortcuts({
  '[': () => {
    collapsed.value = !collapsed.value
  },
})
</script>

<template>
  <UDashboardSidebar
    id="main"
    v-model:collapsed="collapsed"
    collapsible
    resizable
    :min-size="16"
    :default-size="17.5"
    :max-size="22"
    :collapsed-size="4.25"
    :menu="{ title: t('nav.menu'), description: t('nav.menuDescription') }"
    :ui="{ body: 'flex-row gap-0 p-0 overflow-hidden', root: 'bg-default' }"
  >
    <template #default="{ collapsed: isCollapsed }">
      <AppSidebarRail :collapsed="isCollapsed" :account="takeover.shown.value" @expand="collapsed = false" />
      <!-- A page may hold the menu column (Database explorer); the rail stays -->
      <AppSidebarTakeover v-if="!isCollapsed && takeover.shown.value" @collapse="collapsed = true" />
      <AppSidebarMenu v-else-if="!isCollapsed" collapsible @collapse="collapsed = true" />
    </template>
  </UDashboardSidebar>
</template>
