<!--
  Menu column (design: brand + « · MAIN MENU · RESOURCES · SYSTEM · user card).
  The active top-level item gets the black edge bar on the rail border (see useNavigation ACTIVE_BAR).
-->
<script setup lang="ts">
import type { NavigationMenuItem } from '@nuxt/ui'
import { folderColor } from '#shared/utils/forms/folders'

const props = defineProps<{ collapsible?: boolean }>()
const emit = defineEmits<{ collapse: [] }>()
const { t } = useI18n()
const { mainItems, resourceItems, folderItems, systemItems, areaLabel, area } = useNavigation()
// FOLDERS (F11 M4): + creates a folder and opens its page.
const folderOpen = ref(false)
const folderOf = (item: unknown) => (item as { folderColor?: string | null }).folderColor
const sidebarFolders = useSidebarFolders()
function onFolderCreated(folder: { id: string }) {
  sidebarFolders.visit(folder.id)
  void navigateTo(`/folders/${folder.id}`)
}
const mainHeading = computed(() => t(areaLabel.value))
// Back to the page that held this column (Database explorer), main sidebar only
const takeover = useSidebarTakeover()
const colorMode = useColorMode()

const isDark = computed({
  get: () => colorMode.value === 'dark',
  set: value => {
    colorMode.preference = value ? 'dark' : 'light'
  },
})

const systemWithTheme = computed<NavigationMenuItem[]>(() => [
  {
    label: t('nav.darkMode'),
    icon: 'i-lucide-moon',
    slot: 'theme',
    onSelect: (event: Event) => {
      event.preventDefault()
      isDark.value = !isDark.value
    },
  },
  ...systemItems.value,
])

// One group open at a time across all three lists (owner, 2026-10-03): opening a group closes the
// others; the current page's group opens on navigation.
const openGroup = ref<string | undefined>()
const activeGroup = computed(
  () => [...mainItems.value, ...resourceItems.value, ...systemItems.value].find(item => item.children?.length && item.active)?.value as string | undefined,
)
watch(activeGroup, value => (openGroup.value = value), { immediate: true })
const accordion = computed(() => ({
  type: 'single' as const,
  modelValue: openGroup.value,
  'onUpdate:modelValue': (value: unknown) => (openGroup.value = typeof value === 'string' ? value : undefined),
}))

/** Status colour dot for `slot: 'status'` items (see useNavigation). */
const dotClass = (item: unknown) => (item as { dot?: string }).dot

// Shared look for every list, matched to docs/design:
// clean dark labels and icons; chevron and count badge on the right (owner, 2026-10-02); children on a timeline
// (vertical line under the parent icon with a small node per row).
const menuUi = {
  link: 'py-2 text-default hover:text-highlighted',
  linkLeadingIcon: 'text-default',
  linkTrailingIcon: 'size-4 text-muted',
  linkTrailingBadge: 'min-w-5 justify-center px-1 font-normal text-muted',
  childList: 'ms-5 border-s border-default',
  childItem: [
    'relative ps-3 -ms-px',
    'before:absolute before:-start-[3px] before:top-1/2 before:size-1.5 before:-translate-y-1/2 before:rounded-full before:bg-(--ui-border-accented)',
  ].join(' '),
}
</script>

<template>
  <div class="flex min-w-0 flex-1 flex-col">
    <div
      class="flex h-(--ui-header-height) shrink-0 items-center justify-between gap-2 border-b border-default px-3"
    >
      <NuxtLink
        to="/forms"
        class="flex min-w-0 items-center gap-2 rounded-md text-lg font-semibold text-highlighted focus-visible:outline-2 focus-visible:outline-primary"
      >
        <span class="flex size-7 shrink-0 items-center justify-center rounded-md bg-inverted text-inverted">
          <UIcon name="i-lucide-file-check-2" class="size-4" />
        </span>
        <span class="truncate">{{ t('app.name') }}</span>
      </NuxtLink>
      <UTooltip v-if="props.collapsible" :text="t('nav.collapse')" :kbds="['[']">
        <UButton
          icon="i-lucide-chevrons-left"
          color="neutral"
          variant="outline"
          size="xs"
          square
          :aria-label="t('nav.collapse')"
          class="rtl:rotate-180"
          @click="emit('collapse')"
        />
      </UTooltip>
    </div>

    <div class="flex flex-1 flex-col gap-5 overflow-y-auto px-3 py-4">
      <UButton
        v-if="props.collapsible && takeover.owner.value && takeover.dismissed.value"
        :label="takeover.owner.value.title"
        :icon="takeover.owner.value.icon"
        trailing-icon="i-lucide-arrow-right"
        color="neutral"
        variant="outline"
        block
        :ui="{ trailingIcon: 'ms-auto rtl:-scale-x-100' }"
        @click="takeover.dismissed.value = false"
      />
      <nav :aria-label="mainHeading">
        <p class="mb-1 px-2.5 text-xs font-medium text-muted uppercase">{{ mainHeading }}</p>
        <UNavigationMenu :items="mainItems" orientation="vertical" color="neutral" :ui="menuUi" v-bind="accordion">
          <template #status-leading="{ item }">
            <span class="size-2 shrink-0 rounded-[1px]" :class="dotClass(item)" aria-hidden="true" />
          </template>
        </UNavigationMenu>
      </nav>

      <USeparator v-if="resourceItems.length" />

      <nav v-if="resourceItems.length" :aria-label="t('nav.resources')">
        <div class="mb-1 flex items-center justify-between ps-2.5">
          <p class="text-xs font-medium text-muted uppercase">{{ t('nav.resources') }}</p>
          <UButton
            icon="i-lucide-plus"
            color="neutral"
            variant="ghost"
            size="xs"
            square
            to="/templates"
            :aria-label="t('nav.fromTemplate')"
          />
        </div>
        <UNavigationMenu :items="resourceItems" orientation="vertical" color="neutral" :ui="menuUi" v-bind="accordion" />
      </nav>

      <template v-if="area === 'forms'">
        <USeparator />
        <nav :aria-label="t('nav.folders')">
          <div class="mb-1 flex items-center justify-between ps-2.5">
            <!-- The group folds away (remembered per person), like the other groups -->
            <button
              type="button"
              class="flex flex-1 items-center gap-1 rounded-sm text-start text-xs font-medium text-muted uppercase hover:text-highlighted focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :aria-expanded="sidebarFolders.open.value"
              aria-controls="sidebar-folders"
              @click="sidebarFolders.open.value = !sidebarFolders.open.value"
            >
              {{ t('nav.folders') }}
              <UIcon name="i-lucide-chevron-down" class="size-3.5 transition-transform" :class="sidebarFolders.open.value ? '' : '-rotate-90 rtl:rotate-90'" />
            </button>
            <UTooltip :text="t('forms.folders.new')">
              <UButton icon="i-lucide-plus" color="neutral" variant="ghost" size="xs" square :aria-label="t('forms.folders.new')" @click="folderOpen = true" />
            </UTooltip>
          </div>
          <div v-show="sidebarFolders.open.value" id="sidebar-folders">
            <UNavigationMenu v-if="folderItems.length" :items="folderItems" orientation="vertical" color="neutral" :ui="menuUi">
            <template #folder-leading="{ item }">
              <UIcon name="i-lucide-folder" class="size-5 shrink-0" :class="folderColor(folderOf(item)).text" :style="folderColor(folderOf(item)).textStyle" />
            </template>
          </UNavigationMenu>
          </div>
          <UButton v-if="!folderItems.length && sidebarFolders.open.value" :label="t('forms.folders.new')" icon="i-lucide-folder-plus" color="neutral" variant="link" size="sm" class="px-2.5 text-muted" @click="folderOpen = true" />
        </nav>
        <FoldersEditModal v-model:open="folderOpen" @saved="onFolderCreated" />
      </template>

      <!-- A line above SYSTEM (owner 2026-10-05), which stays at the bottom -->
      <USeparator class="mt-auto" />
      <nav :aria-label="t('nav.system')">
        <p class="mb-1 px-2.5 text-xs font-medium text-muted uppercase">{{ t('nav.system') }}</p>
        <UNavigationMenu :items="systemWithTheme" orientation="vertical" color="neutral" :ui="menuUi" v-bind="accordion">
          <template #theme-trailing>
            <USwitch
              :model-value="isDark"
              size="sm"
              tabindex="-1"
              aria-hidden="true"
              class="pointer-events-none"
            />
          </template>
        </UNavigationMenu>
      </nav>
    </div>

    <div class="shrink-0 border-t border-default p-3">
      <AppUserMenu />
    </div>
  </div>
</template>
