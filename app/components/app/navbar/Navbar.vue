<!-- Shared navbar: breadcrumbs, search, notifications, language and theme switches (rules 8, 9). -->
<script setup lang="ts">
const { t } = useI18n()
const { notificationsOpen } = useAppUi()
</script>

<template>
  <UDashboardNavbar :ui="{ title: 'min-w-0' }">
    <template #leading>
      <UDashboardSidebarCollapse class="hidden lg:inline-flex" />
    </template>

    <template #title>
      <AppBreadcrumbs />
    </template>

    <template #right>
      <UDashboardSearchButton :label="t('search.button')" class="hidden md:inline-flex" />
      <UDashboardSearchButton collapsed class="md:hidden" :aria-label="t('search.button')" />
      <UTooltip :text="t('navbar.notifications')">
        <UButton
          icon="i-lucide-bell"
          color="neutral"
          variant="ghost"
          :aria-label="t('navbar.notifications')"
          @click="notificationsOpen = true"
        />
      </UTooltip>
      <AppLocaleSwitch class="hidden sm:inline-flex" />
      <UColorModeButton />
    </template>
  </UDashboardNavbar>
</template>
