<!-- Command palette (Ctrl/⌘+K): pages, actions, language. Theme toggle is built into UDashboardSearch. -->
<script setup lang="ts">
import type { CommandPaletteGroup, CommandPaletteItem } from '@nuxt/ui'

const { t } = useI18n()
const { destinations } = useNavigation()
const { shortcutsOpen } = useAppUi()
const { locales, changeLocale } = useAppLocale()

const groups = computed<CommandPaletteGroup<CommandPaletteItem>[]>(() => [
  {
    id: 'pages',
    label: t('search.pages'),
    items: destinations.value.map(item => ({
      label: t(`nav.${item.key}`),
      icon: item.icon,
      to: item.to,
      kbds: item.shortcut?.split('-'),
    })),
  },
  {
    id: 'actions',
    label: t('search.actions'),
    items: [
      {
        label: t('shortcuts.title'),
        icon: 'i-lucide-keyboard',
        kbds: ['?'],
        onSelect: () => {
          shortcutsOpen.value = true
        },
      },
      {
        label: t('search.changeLanguage'),
        icon: 'i-lucide-languages',
        children: locales.map(locale => ({
          label: locale.name,
          suffix: locale.englishName,
          icon: locale.flag,
          onSelect: () => changeLocale(locale.code),
        })),
      },
    ],
  },
])
// title/description are passed explicitly: Nuxt UI 4.11 ships no `dashboardSearch.title` message.
</script>

<template>
  <UDashboardSearch
    :groups="groups"
    :title="t('search.title')"
    :description="t('search.placeholder')"
    :placeholder="t('search.placeholder')"
  />
</template>
