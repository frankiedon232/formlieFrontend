<!--
  Sidebar: expanded menu ↔ collapsed icon rail (remembered in a cookie by UDashboardGroup).
  Collapsed + hover/keyboard focus → full menu peeks over the page (AppSidebarPeek, a sibling
  in the layout). Phones: slide-over drawer. `[` toggles collapse.
-->
<script setup lang="ts">
const emit = defineEmits<{ peekFocus: [edge: 'first' | 'last'] }>()
const { t } = useI18n()
const { open: peekOpen, collapsed: sharedCollapsed, available, schedule, close } = useSidebarPeek()
const collapsed = ref(false)

watch(
  collapsed,
  value => {
    sharedCollapsed.value = value
    close()
  },
  { immediate: true },
)

const sidebarEl = ref<HTMLElement | null>(null)
onMounted(() => {
  sidebarEl.value = document.getElementById(SIDEBAR_ELEMENT_ID)
})

useEventListener(sidebarEl, 'mouseenter', () => schedule(true))
useEventListener(sidebarEl, 'mouseleave', () => schedule(false))
useEventListener(sidebarEl, 'focusin', (event: FocusEvent) => {
  if (!available.value || peekOpen.value) return
  if (!(event.target as HTMLElement).matches(':focus-visible')) return
  const from = event.relatedTarget as Node | null
  // Coming back with Shift+Tab from the page → land on the peek's last item.
  const fromAfter =
    !!from &&
    !!sidebarEl.value &&
    !!(sidebarEl.value.compareDocumentPosition(from) & Node.DOCUMENT_POSITION_FOLLOWING)
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
    :min-size="14"
    :default-size="16"
    :max-size="22"
    :collapsed-size="4.5"
    :menu="{ title: t('nav.menu'), description: t('nav.menuDescription') }"
    :ui="{ footer: 'border-t border-default', header: collapsed ? 'justify-center' : '' }"
  >
    <template #header="{ collapsed: isCollapsed }">
      <AppSidebarBrand :collapsed="isCollapsed" />
    </template>

    <template #default="{ collapsed: isCollapsed }">
      <AppSidebarNav :collapsed="isCollapsed" />
    </template>

    <template #footer="{ collapsed: isCollapsed }">
      <AppSidebarFooter :collapsed="isCollapsed" />
    </template>
  </UDashboardSidebar>
</template>
