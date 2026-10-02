<!--
  Menu column (design: brand + « · MAIN MENU · RESOURCES · SYSTEM · user card).
  The active top-level item gets the black edge bar on the rail border (see useNavigation ACTIVE_BAR).
-->
<script setup lang="ts">
import type { NavigationMenuItem } from '@nuxt/ui'

const props = defineProps<{ collapsible?: boolean }>()
const emit = defineEmits<{ collapse: [] }>()
const { t } = useI18n()
const { mainItems, resourceItems, systemItems, area } = useNavigation()
const mainHeading = computed(() => (area.value === 'data' ? t('nav.dataSources') : t('nav.main')))
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
      <nav :aria-label="mainHeading">
        <p class="mb-1 px-2.5 text-xs font-medium text-muted uppercase">{{ mainHeading }}</p>
        <UNavigationMenu :items="mainItems" orientation="vertical" color="neutral" :ui="menuUi">
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
        <UNavigationMenu :items="resourceItems" orientation="vertical" color="neutral" :ui="menuUi" />
      </nav>

      <nav :aria-label="t('nav.system')" class="mt-auto">
        <p class="mb-1 px-2.5 text-xs font-medium text-muted uppercase">{{ t('nav.system') }}</p>
        <UNavigationMenu :items="systemWithTheme" orientation="vertical" color="neutral" :ui="menuUi">
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
