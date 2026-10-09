<!--
  Page header bar (owner, 2026-10-02: titles, subtitles, crumbs and page buttons live here so the
  content area stays clear). Left: title + (breadcrumbs · subtitle). Right: search, page actions,
  language, notifications, theme (below lg, where the sidebar's Dark mode switch is hidden), team
  avatars and Invite member (owners and admins).
  Phones: title only; page action buttons collapse to icons.
-->
<script setup lang="ts">
const props = defineProps<{
  title: string
  subtitle?: string
  subtitleIcon?: string
  subtitleIconClass?: string
  subtitleIconStyle?: Record<string, string>
  /** Search as an icon button at every width (headers with many actions). */
  compactSearch?: boolean
}>()

const { t } = useI18n()
const { notificationsOpen } = useAppUi()
// The bell's unread count, checked every minute (F14 M4)
const notifications = useNotifications()
onMounted(notifications.start)
const unread = computed(() => notifications.feed.value?.unread ?? 0)
const { items: crumbs } = useBreadcrumbs()
const { current, locales, locale, changeLocale } = useAppLocale()

/** On a top-level page the only crumb is the title itself, so show the trail from depth 2. */
// Settings → Appearance can hide the breadcrumbs and the search field
const look = useAppearance().current
const showCrumbs = computed(() => crumbs.value.length > 1 && look.value.header.breadcrumbs)

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
  <UDashboardNavbar :ui="{ root: 'gap-3', left: 'min-w-0 flex-1', right: 'gap-2 shrink-0' }">
    <template #title>
      <div class="min-w-0">
        <!-- #title: e.g. an inline-editable name (builder); defaults to the plain title. -->
        <slot name="title">
          <h1 class="truncate text-base font-semibold text-highlighted sm:text-lg">{{ props.title }}</h1>
        </slot>
        <div
          v-if="showCrumbs || props.subtitle || $slots.meta"
          class="hidden min-w-0 items-center gap-1.5 text-xs text-muted sm:flex"
        >
          <AppBreadcrumbs v-if="showCrumbs" class="min-w-0 shrink-0" compact />
          <span v-if="showCrumbs && props.subtitle && !$slots.meta" aria-hidden="true">·</span>
          <span v-if="showCrumbs && $slots.meta" aria-hidden="true">·</span>
          <!-- #meta: live status line (design: "Last sync: Just now"), e.g. "Draft · Saved just now". -->
          <slot name="meta">
            <span v-if="props.subtitle" class="flex min-w-0 items-center gap-1 truncate">
              <UIcon v-if="props.subtitleIcon" :name="props.subtitleIcon" class="size-3 shrink-0" :class="props.subtitleIconClass" :style="props.subtitleIconStyle" />
              <span class="truncate">{{ props.subtitle }}</span>
            </span>
          </slot>
        </div>
      </div>
    </template>

    <template #right>
      <UDashboardSearchButton
        v-if="look.header.search"
        :label="t('search.anything')"
        color="neutral"
        variant="outline"
        class="hidden w-48 justify-start text-dimmed xl:w-60"
        :class="props.compactSearch ? '' : 'lg:inline-flex'"
        :ui="{ trailing: 'ms-auto' }"
      />
      <UDashboardSearchButton
        v-if="look.header.search"
        collapsed
        color="neutral"
        variant="outline"
        :class="props.compactSearch ? '' : 'lg:hidden'"
        :aria-label="t('search.button')"
      />

      <!-- Page actions: labels hide on phones, icons stay (layout utility only). -->
      <div v-if="$slots.actions" class="flex items-center gap-2 max-sm:[&_[data-slot=label]]:hidden">
        <USeparator orientation="vertical" class="hidden h-6 sm:block" />
        <slot name="actions" />
        <USeparator orientation="vertical" class="hidden h-6 sm:block" />
      </div>

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
            class="hidden sm:inline-flex"
            :aria-label="`${t('common.language')}: ${current.name}`"
          />
        </UTooltip>
      </UDropdownMenu>

      <UTooltip :text="t('navbar.notifications')">
        <UChip :show="!!unread" :text="unread > 9 ? '9+' : unread" color="error" size="3xl" inset>
          <UButton
            icon="i-lucide-bell"
            color="neutral"
            variant="outline"
            square
            :aria-label="unread ? t('notifications.bellUnread', { n: unread }, unread) : t('navbar.notifications')"
            @click="notificationsOpen = true"
          />
        </UChip>
      </UTooltip>

      <UColorModeButton color="neutral" variant="outline" class="lg:hidden" />

      <!-- Team avatars and Invite member, after the bell as in the design (F16 M4) -->
      <AppNavbarTeam />
    </template>
  </UDashboardNavbar>
</template>
