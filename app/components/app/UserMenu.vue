<!--
  Account card (design: avatar · name · email · ⇅). `compact` = avatar only (collapsed rail).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

const props = defineProps<{ compact?: boolean }>()
const { t } = useI18n()
const colorMode = useColorMode()
const { shortcutsOpen } = useAppUi()
const { locale, locales, current, changeLocale } = useAppLocale()

const session = useSession()
const auth = useAuth()
const user = computed(() => ({
  name: session.displayName.value || t('user.guest'),
  email: session.user.value?.email ?? t('user.notSignedIn'),
}))

async function logout() {
  await auth.logout()
  await navigateTo('/auth/login')
}
const avatar = computed(() => ({ alt: user.value.name }))

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
  [{ type: 'label', label: user.value.name, description: user.value.email, avatar: avatar.value }],
  [
    { label: t('user.profile'), icon: 'i-lucide-circle-user', to: '/profile' },
    { label: t('nav.settings'), icon: 'i-lucide-settings', to: '/settings' },
    ...(session.user.value?.role === 'member'
      ? []
      : [{ label: t('onboarding.menu'), icon: 'i-lucide-list-checks', to: '/onboarding' }]),
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
      label: t('common.language'),
      icon: current.value.flag,
      children: locales.map(item => ({
        label: item.name,
        description: item.englishName,
        icon: item.flag,
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
  [{ label: t('user.logout'), icon: 'i-lucide-log-out', color: 'error', onSelect: logout }],
])
</script>

<template>
  <UDropdownMenu
    :items="items"
    :content="{
      side: props.compact ? 'right' : 'top',
      align: props.compact ? 'end' : 'start',
      collisionPadding: 12,
    }"
    :ui="{ content: 'w-60' }"
  >
    <UButton
      v-if="props.compact"
      :avatar="avatar"
      color="neutral"
      variant="ghost"
      square
      :aria-label="t('user.account')"
    />
    <UButton
      v-else
      color="neutral"
      variant="ghost"
      block
      class="justify-between gap-2 p-1.5 text-start"
      :aria-label="t('user.account')"
    >
      <UUser
        :name="user.name"
        :description="user.email"
        :avatar="avatar"
        size="md"
        class="min-w-0"
        :ui="{ wrapper: 'min-w-0 text-start', name: 'truncate', description: 'truncate' }"
      />
      <UIcon
        name="i-lucide-chevrons-up-down"
        class="size-6 shrink-0 rounded-md p-1 text-muted ring ring-default"
        aria-hidden="true"
      />
    </UButton>
  </UDropdownMenu>
</template>
