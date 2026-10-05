<!--
  Command palette (Ctrl/⌘+K): pages, every folder (F11 M4: any folder one search away, however many
  there are; each in its colour with its form count), actions, language. Theme toggle is built into
  UDashboardSearch.
-->
<script setup lang="ts">
import type { CommandPaletteGroup, CommandPaletteItem } from '@nuxt/ui'
import { folderColor } from '#shared/utils/forms/folders'

const { t } = useI18n()
const { destinations } = useNavigation()
const { shortcutsOpen } = useAppUi()
const { locales, changeLocale } = useAppLocale()
const { counts } = useNavCounts()
const folderOf = (item: unknown) => (item as { folderColor?: string | null }).folderColor

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
  ...(counts.value?.folders?.length
    ? [
        {
          id: 'folders',
          label: t('nav.folders'),
          items: counts.value.folders.map(folder => ({
            label: folder.name,
            icon: 'i-lucide-folder',
            slot: 'folder' as const,
            folderColor: folder.color,
            suffix: t('forms.folders.count', { count: folder.count }, folder.count),
            to: `/folders/${folder.id}`,
          })),
        },
      ]
    : []),
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
  >
    <!-- Folders in their colour (custom colours are an inline style) -->
    <template #folder-leading="{ item }">
      <UIcon name="i-lucide-folder" class="size-5 shrink-0" :class="folderColor(folderOf(item)).text" :style="folderColor(folderOf(item)).textStyle" />
    </template>
  </UDashboardSearch>
</template>
