<!-- Account menu. Name/avatar and log out are wired to the session in F3. -->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

defineProps<{ collapsed?: boolean }>()
const { t } = useI18n()
const colorMode = useColorMode()
const { shortcutsOpen } = useAppUi()
const { locale, locales, changeLocale } = useAppLocale()

const user = computed(() => ({ name: t('user.guest'), email: '' }))

const themeItem = (value: 'light' | 'dark' | 'system', icon: string): DropdownMenuItem => ({
  label: t(`user.${value}`),
  icon,
  type: 'checkbox',
  checked: colorMode.preference === value,
  onSelect: (event: Event) => {
    event.preventDefault()
    colorMode.preference = value
  },
})

const items = computed<DropdownMenuItem[][]>(() => [
  [{ type: 'label', label: user.value.name, avatar: { alt: user.value.name, icon: 'i-lucide-user' } }],
  [
    { label: t('user.profile'), icon: 'i-lucide-circle-user', to: '/profile' },
    { label: t('nav.settings'), icon: 'i-lucide-settings', to: '/settings' },
  ],
  [
    {
      label: t('user.theme'),
      icon: 'i-lucide-sun-moon',
      children: [
        themeItem('light', 'i-lucide-sun'),
        themeItem('dark', 'i-lucide-moon'),
        themeItem('system', 'i-lucide-monitor'),
      ],
    },
    {
      // Also here so phones (no navbar language switch below sm) can change language.
      label: t('common.language'),
      icon: 'i-lucide-languages',
      children: locales.map(item => ({
        label: item.name,
        description: item.englishName,
        type: 'checkbox' as const,
        checked: locale.value === item.code,
        onSelect: () => changeLocale(item.code),
      })),
      content: { class: 'max-h-80 overflow-y-auto' },
    },
    {
      label: t('shortcuts.title'),
      icon: 'i-lucide-keyboard',
      kbds: ['?'],
      onSelect: () => {
        shortcutsOpen.value = true
      },
    },
  ],
  [{ label: t('user.logout'), icon: 'i-lucide-log-out', color: 'error', disabled: true }],
])
</script>

<template>
  <UDropdownMenu
    :items="items"
    :content="{ align: 'center', collisionPadding: 12 }"
    :ui="{ content: collapsed ? 'w-48' : 'w-(--reka-dropdown-menu-trigger-width)' }"
  >
    <UButton
      :avatar="{ alt: user.name, icon: 'i-lucide-user' }"
      :label="collapsed ? undefined : user.name"
      :trailing-icon="collapsed ? undefined : 'i-lucide-chevrons-up-down'"
      :aria-label="t('user.account')"
      color="neutral"
      variant="ghost"
      block
      :square="collapsed"
      class="data-[state=open]:bg-elevated"
      :ui="{ trailingIcon: 'text-dimmed' }"
    />
  </UDropdownMenu>
</template>
