<!--
  Account card (design: avatar · name · email · ⇅). `compact` = avatar only (collapsed rail); `large` = a bigger avatar (foot of the rail).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { Onboarding } from '#shared/types/onboarding'

const props = defineProps<{ compact?: boolean; large?: boolean }>()
const { t } = useI18n()
const { roleName } = useBuiltInNames()
const colorMode = useColorMode()
const { shortcutsOpen } = useAppUi()
const { locale, locales, current, changeLocale } = useAppLocale()

const session = useSession()
const auth = useAuth()
const user = computed(() => ({
  name: session.displayName.value || t('user.guest'),
  email: session.user.value?.email ?? t('user.notSignedIn'),
  role: roleName(session.user.value?.role, session.user.value?.role_name),
}))

async function logout() {
  await auth.logout()
  await navigateTo('/auth/login')
}
const { can } = useCan()
const avatar = computed(() => ({ alt: user.value.name, src: session.user.value?.avatar_url ?? undefined }))

// "Workspace setup" only while the set-up isn't finished (owner 2026-10-10); asked once, quietly
const api = useApi()
const setupOpen = ref(false)
onMounted(async () => {
  if (!can('settings.manage')) return
  try {
    setupOpen.value = (await api.get<Onboarding>('/onboarding', undefined, { background: true })).data.status !== 'completed'
  } catch {
    // Unknown: the item stays hidden; the set-up is still reachable from Settings
  }
})

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
  [{ type: 'label', slot: 'account' as const, label: user.value.name, avatar: avatar.value }],
  [
    { label: t('user.profile'), icon: 'i-lucide-circle-user', to: '/profile' },
    ...(can('settings.view') ? [{ label: t('nav.settings'), icon: 'i-lucide-settings', to: '/settings' }] : []),
    ...(can('settings.manage') && setupOpen.value ? [{ label: t('onboarding.menu'), icon: 'i-lucide-list-checks', to: '/onboarding' }] : []),
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
    <!-- Name, email and the person's role (Roles & access) at the top of the menu -->
    <template #account-label>
      <span class="block truncate text-highlighted">{{ user.name }}</span>
      <span class="block truncate text-xs font-normal text-muted">{{ user.email }}</span>
      <UBadge v-if="user.role" :label="user.role" icon="i-lucide-shield" color="neutral" variant="outline" size="sm" class="mt-1.5" />
    </template>
    <UButton
      v-if="props.compact"
      :avatar="{ ...avatar, size: props.large ? 'lg' : undefined }"
      color="neutral"
      variant="ghost"
      :size="props.large ? 'lg' : undefined"
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
