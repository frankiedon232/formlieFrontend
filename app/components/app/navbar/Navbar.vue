<!--
  Top bar (docs/design): search field + breadcrumbs on the left; language, notifications and the global
  "New form" action on the right. Phones: menu toggle + compact icons (+ theme, since the
  sidebar's Dark mode switch lives in the drawer).
-->
<script setup lang="ts">
const { t } = useI18n()
const { notificationsOpen } = useAppUi()
const { current, locales, locale, changeLocale } = useAppLocale()

const languageItems = computed(() =>
  locales.map(item => ({
    label: item.name,
    description: item.englishName,
    icon: item.flag,
    type: 'checkbox' as const,
    checked: locale.value === item.code,
    onSelect: () => changeLocale(item.code),
  })),
)
</script>

<template>
  <UDashboardNavbar :ui="{ root: 'gap-3', left: 'min-w-0 flex-1', right: 'gap-2' }">
    <template #leading>
      <UDashboardSearchButton
        :label="t('search.anything')"
        color="neutral"
        variant="outline"
        class="hidden w-64 justify-start text-dimmed sm:inline-flex"
        :ui="{ trailing: 'ms-auto' }"
      />
      <UDashboardSearchButton collapsed class="sm:hidden" :aria-label="t('search.button')" />
      <USeparator orientation="vertical" class="mx-1 hidden h-6 sm:block" />
      <AppBreadcrumbs class="min-w-0" />
    </template>

    <template #right>
      <UDropdownMenu
        :items="languageItems"
        :content="{ align: 'end' }"
        :ui="{ content: 'max-h-80 w-56 overflow-y-auto' }"
      >
        <UTooltip :text="current.name">
          <UButton
            :icon="current.flag"
            color="neutral"
            variant="outline"
            square
            :aria-label="`${t('common.language')}: ${current.name}`"
          />
        </UTooltip>
      </UDropdownMenu>

      <UTooltip :text="t('navbar.notifications')">
        <UButton
          icon="i-lucide-bell"
          color="neutral"
          variant="outline"
          square
          :aria-label="t('navbar.notifications')"
          @click="notificationsOpen = true"
        />
      </UTooltip>

      <UColorModeButton color="neutral" variant="outline" class="lg:hidden" />

      <USeparator orientation="vertical" class="hidden h-6 sm:block" />

      <UButton
        icon="i-lucide-plus"
        :label="t('nav.newForm')"
        color="neutral"
        variant="outline"
        to="/forms/new"
        class="hidden sm:inline-flex"
      />
    </template>
  </UDashboardNavbar>
</template>
