<!--
  Far-left rail (design: ⋯ · + · workspaces). When the menu is collapsed it also carries the
  section icons with tooltips, an expand button and the account avatar.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

const props = defineProps<{ collapsed?: boolean }>()
const emit = defineEmits<{ expand: [] }>()
const { t } = useI18n()
const { destinations, isActive } = useNavigation()
const { shortcutsOpen } = useAppUi()
const railNavId = RAIL_NAV_ID

const moreItems = computed<DropdownMenuItem[][]>(() => [
  [
    {
      label: t('shortcuts.title'),
      icon: 'i-lucide-keyboard',
      kbds: ['?'],
      onSelect: () => {
        shortcutsOpen.value = true
      },
    },
    { label: t('nav.help'), icon: 'i-lucide-circle-help', to: '/help' },
  ],
])

const createItems = computed<DropdownMenuItem[][]>(() => [
  [
    { label: t('nav.newForm'), icon: 'i-lucide-file-plus', to: '/forms/new' },
    { label: t('nav.fromTemplate'), icon: 'i-lucide-layout-template', to: '/templates' },
  ],
])

// Current workspace; the organisation switcher (several orgs per tenant) joins in F11.
const tenant = useTenant()
const workspaces = computed(() => [
  { name: tenant.profile.value?.name ?? t('app.name'), icon: 'i-lucide-building-2', active: true },
])
</script>

<template>
  <div class="flex w-17 shrink-0 flex-col items-center gap-3 border-e border-default py-4">
    <UDropdownMenu :items="moreItems" :content="{ side: 'right', align: 'start' }">
      <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" :aria-label="t('nav.more')" />
    </UDropdownMenu>

    <UDropdownMenu :items="createItems" :content="{ side: 'right', align: 'start' }">
      <UButton
        icon="i-lucide-plus"
        color="neutral"
        variant="solid"
        size="lg"
        square
        :aria-label="t('nav.create')"
      />
    </UDropdownMenu>

    <USeparator class="w-8" />

    <nav :aria-label="t('nav.workspaces')" class="flex flex-col items-center gap-3">
      <UTooltip
        v-for="workspace in workspaces"
        :key="workspace.name"
        :text="workspace.name"
        :content="{ side: 'right' }"
      >
        <UButton
          to="/forms"
          :icon="workspace.icon"
          color="neutral"
          variant="outline"
          size="lg"
          square
          :aria-label="workspace.name"
          :aria-current="workspace.active ? 'true' : undefined"
          :class="workspace.active ? 'ring-2 ring-inverted' : ''"
        />
      </UTooltip>
    </nav>

    <template v-if="props.collapsed">
      <USeparator class="w-8" />
      <nav
        :id="railNavId"
        :aria-label="t('nav.main')"
        class="flex flex-1 flex-col items-center gap-1 overflow-y-auto"
      >
        <UTooltip
          v-for="item in destinations"
          :key="item.key"
          :text="t(`nav.${item.key}`)"
          :content="{ side: 'right' }"
        >
          <UButton
            :to="item.to"
            :icon="item.icon"
            color="neutral"
            :variant="isActive(item) ? 'soft' : 'ghost'"
            :aria-label="t(`nav.${item.key}`)"
            :ui="item.iconClass ? { leadingIcon: item.iconClass } : undefined"
          />
        </UTooltip>
      </nav>
      <UTooltip :text="t('nav.expand')" :kbds="['[']" :content="{ side: 'right' }">
        <UButton
          icon="i-lucide-chevrons-right"
          color="neutral"
          variant="outline"
          size="sm"
          square
          :aria-label="t('nav.expand')"
          class="rtl:rotate-180"
          @click="emit('expand')"
        />
      </UTooltip>
      <AppUserMenu compact />
    </template>
  </div>
</template>
