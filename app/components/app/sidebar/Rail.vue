<!--
  Far-left rail (design: ⋯ · + · workspaces), then the other areas (Data sources, API service, AI assistant), each with
  its own menu; the workspace button is the Forms area. When the menu is collapsed it also carries the current area's section icons
  with tooltips. Its foot stays in place: expand (folded), Help & support (always, owner 2026-10-05) and the account avatar
  (folded, or while a page holds the menu column, e.g. the Database explorer).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

const props = defineProps<{ collapsed?: boolean; account?: boolean }>()
const emit = defineEmits<{ expand: [] }>()
const { t } = useI18n()
// Settings → Appearance: a dark rail wears Nuxt UI's dark tokens
const look = useAppearance().current
const { areaDestinations, area, areas, isActive } = useNavigation()
const { shortcutsOpen } = useAppUi()
const railNavId = RAIL_NAV_ID
const route = useRoute()
const accountHere = computed(() => props.collapsed || props.account)
const helpActive = computed(() => route.path === '/help' || route.path.startsWith('/help/'))

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
    { type: 'label' as const, label: t('nav.createForms') },
    { label: t('nav.newForm'), icon: 'i-lucide-file-plus', to: '/forms/new' },
    { label: t('nav.fromTemplate'), icon: 'i-lucide-layout-template', to: '/templates' },
    { label: t('nav.newTemplate'), icon: 'i-lucide-bookmark-plus', to: { path: '/forms/new', query: { purpose: 'template' } } },
  ],
  [
    { type: 'label' as const, label: t('nav.createOperations') },
    { label: t('nav.addDatabase'), icon: 'i-lucide-database', to: '/data-sources/connections/new' },
    { label: t('nav.newApiService'), icon: 'i-lucide-boxes', to: { path: '/api-service/services', query: { new: '1' } } },
    { label: t('nav.dataQuery'), icon: 'i-lucide-square-terminal', to: '/data-sources/query' },
    { label: t('nav.dataExplorer'), icon: 'i-lucide-table-2', to: '/data-sources/explorer' },
  ],
])

// The workspace, and with several organisations a switcher that narrows the portal to one (F14 M7)
const tenant = useTenant()
const session = useSession()
const organisations = useOrganisations()
const workspaces = computed(() => [
  { name: tenant.profile.value?.name ?? t('app.name'), icon: 'i-lucide-building-2', active: true },
])
const orgLabel = computed(() => organisations.current.value?.name ?? t('organisations.all'))
const orgItems = computed<DropdownMenuItem[][]>(() => [
  [
    { type: 'label' as const, label: t('organisations.title') },
    { label: t('organisations.all'), icon: 'i-lucide-layers', type: 'checkbox' as const, checked: !organisations.currentId.value, onSelect: () => organisations.choose(null) },
    ...organisations.active.value.map(org => ({ label: org.name, avatar: org.logo_url ? { src: org.logo_url, alt: '' } : { text: organisationInitials(org), alt: '' }, type: 'checkbox' as const, checked: organisations.currentId.value === org.id, onSelect: () => organisations.choose(org.id) })),
  ],
  ...(session.user.value?.role !== 'member' ? [[{ label: t('organisations.manage'), icon: 'i-lucide-settings-2', to: '/settings/organisations' }]] : []),
])
</script>

<template>
  <div class="flex w-17 shrink-0 flex-col border-e border-default" :class="look.rail === 'dark' ? 'dark bg-default text-default' : ''">
    <!-- Top: ⋯ · + · workspace · areas (and the area's sections when the menu is folded); scrolls if needed -->
    <div class="flex min-h-0 flex-1 flex-col items-center gap-3 overflow-y-auto py-4">
      <UDropdownMenu :items="moreItems" :content="{ side: 'right', align: 'start' }">
        <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" :aria-label="t('nav.more')" />
      </UDropdownMenu>

      <UDropdownMenu :items="createItems" :content="{ side: 'right', align: 'start' }">
        <UButton icon="i-lucide-plus" color="neutral" variant="solid" size="lg" square :aria-label="t('nav.create')" />
      </UDropdownMenu>

      <USeparator class="w-8" />

      <nav :aria-label="t('nav.workspaces')" class="flex flex-col items-center gap-3">
        <UDropdownMenu v-if="organisations.several.value" :items="orgItems" :content="{ side: 'right', align: 'start' }" :ui="{ content: 'max-h-96 w-64 overflow-y-auto' }">
          <UTooltip :text="t('organisations.switch', { name: orgLabel })" :content="{ side: 'right' }">
            <UButton color="neutral" variant="outline" size="lg" square :aria-label="t('organisations.switch', { name: orgLabel })" class="relative">
              <img v-if="organisations.current.value?.logo_url" :src="organisations.current.value.logo_url" alt="" class="size-5 rounded object-contain">
              <span v-else-if="organisations.current.value" class="text-[11px] font-semibold">{{ organisationInitials(organisations.current.value) }}</span>
              <UIcon v-else name="i-lucide-layers" class="size-5" />
              <span class="absolute -end-1 -bottom-1 flex size-3.5 items-center justify-center rounded-full bg-inverted text-inverted"><UIcon name="i-lucide-chevrons-up-down" class="size-2.5" /></span>
            </UButton>
          </UTooltip>
        </UDropdownMenu>
        <UTooltip v-for="workspace in workspaces" :key="workspace.name" :text="workspace.name" :content="{ side: 'right' }">
          <UButton
            to="/forms"
            :icon="workspace.icon"
            color="neutral"
            variant="outline"
            size="lg"
            square
            :aria-label="workspace.name"
            :aria-current="area === 'forms' ? 'true' : undefined"
            :class="area === 'forms' ? 'ring-2 ring-inverted' : ''"
          />
        </UTooltip>
      </nav>

      <nav :aria-label="t('nav.areas')" class="flex flex-col items-center gap-3">
        <UTooltip v-for="item in areas" :key="item.key" :text="t(item.label)" :content="{ side: 'right' }">
          <UButton
            :to="item.to"
            :icon="item.icon"
            color="neutral"
            variant="outline"
            size="lg"
            square
            :aria-label="t(item.label)"
            :aria-current="area === item.key ? 'page' : undefined"
            :class="area === item.key ? 'ring-2 ring-inverted' : ''"
          />
        </UTooltip>
      </nav>

      <template v-if="props.collapsed">
        <USeparator class="w-8" />
        <nav :id="railNavId" :aria-label="t('nav.main')" class="flex flex-col items-center gap-1">
          <UTooltip v-for="item in areaDestinations" :key="item.key" :text="t(`nav.${item.key}`)" :content="{ side: 'right' }">
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
      </template>
    </div>

    <!-- Foot, always in place (owner 2026-10-05): expand (menu folded) · Help & support · the account
         (when the menu column doesn't show it: folded, or held by a page such as the explorer), with
         short lines between them. Without the account here, Help sits in a box as tall as the menu's
         account card, so their lines meet. -->
    <div class="flex shrink-0 flex-col items-center">
      <template v-if="props.collapsed">
        <USeparator class="w-8" />
        <div class="flex justify-center py-2">
          <UTooltip :text="t('nav.expand')" :kbds="['[']" :content="{ side: 'right' }">
            <UButton icon="i-lucide-chevrons-right" color="neutral" variant="ghost" square :aria-label="t('nav.expand')" class="rtl:rotate-180" @click="emit('expand')" />
          </UTooltip>
        </div>
      </template>
      <USeparator class="w-8" />
      <div class="flex items-center justify-center" :class="accountHere ? 'py-2' : 'h-18'">
        <UTooltip :text="t('nav.help')" :content="{ side: 'right' }">
          <UButton
            to="/help"
            icon="i-lucide-circle-help"
            color="neutral"
            :variant="helpActive ? 'soft' : 'ghost'"
            size="lg"
            square
            :aria-label="t('nav.help')"
            :aria-current="helpActive ? 'page' : undefined"
          />
        </UTooltip>
      </div>
      <template v-if="accountHere">
        <USeparator class="w-8" />
        <div class="flex h-18 items-center justify-center">
          <AppUserMenu compact large />
        </div>
      </template>
    </div>
  </div>
</template>
