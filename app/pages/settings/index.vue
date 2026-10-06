<!--
  Settings overview (F14): the workspace at a glance (its logo, name and address, how far its setup
  is as a ring, the next step worth taking, the setup checklist), then every section in its group as
  a card with its live status, or "Soon" with the milestone that brings it. Admins only.
-->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.settings' })
const { t } = useI18n()
useHead({ title: () => t('nav.settings') })
const session = useSession()
const tenant = useTenant()
const isAdmin = computed(() => session.user.value?.role !== 'member')
const store = useWorkspaceSettings()
onMounted(() => isAdmin.value && void store.load().catch(() => {}))
const { groups, label, description } = useSettingsSections()
const { statusOf, setup, next } = useSettingsStatus(store.settings)
const address = computed(() => (tenant.profile.value?.subdomain ? tenant.hostUrl(tenant.profile.value.subdomain).replace(/^https?:\/\//, '').replace(/\/$/, '') : ''))
const DOT = { done: 'bg-success', partial: 'bg-warning', todo: 'bg-(--ui-border-accented)', info: 'bg-(--ui-border-accented)' } as const
// Ring: circumference of r = 26
const RING = 2 * Math.PI * 26
</script>

<template>
  <SettingsPage id="settings" :title="t('nav.settings')" :subtitle="t('settings.desc.overview')" icon="i-lucide-settings">
    <AppEmpty v-if="!isAdmin" icon="i-lucide-lock-keyhole" :title="t('settings.adminsOnly')" :description="t('settings.adminsOnlyDesc')" :actions="[{ label: t('nav.profile'), icon: 'i-lucide-user-round', color: 'neutral', variant: 'outline', to: '/profile' }]" />
    <AppEmpty v-else-if="store.failed.value && !store.settings.value" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => store.load(true) }]" />
    <template v-else>
      <!-- The workspace at a glance -->
      <USkeleton v-if="!store.settings.value" class="h-36 rounded-xl" />
      <div v-else class="flex flex-col gap-5 rounded-xl border border-default p-4 sm:flex-row sm:items-center sm:p-5">
        <div class="flex min-w-0 flex-1 items-center gap-4">
          <span class="flex size-14 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-default bg-elevated">
            <img v-if="store.settings.value.branding.logo_url" :src="store.settings.value.branding.logo_url" :alt="store.settings.value.company.display_name" class="max-h-full max-w-full object-contain p-1.5">
            <span v-else class="text-xl font-semibold text-highlighted">{{ store.settings.value.company.display_name.slice(0, 1).toUpperCase() }}</span>
          </span>
          <div class="flex min-w-0 flex-col gap-0.5">
            <span class="truncate text-lg font-semibold text-highlighted">{{ store.settings.value.company.display_name }}</span>
            <span v-if="address" class="truncate font-mono text-xs text-muted" dir="ltr">{{ address }}</span>
            <span v-if="store.settings.value.company.legal_name !== store.settings.value.company.display_name" class="truncate text-xs text-muted">{{ store.settings.value.company.legal_name }}</span>
          </div>
        </div>
        <div class="flex items-center gap-4 sm:border-s sm:border-default sm:ps-5">
          <div class="relative size-16 shrink-0" role="img" :aria-label="t('settings.setup', { n: setup })">
            <svg viewBox="0 0 64 64" class="size-16 -rotate-90" aria-hidden="true">
              <circle cx="32" cy="32" r="26" fill="none" stroke-width="6" class="stroke-(--ui-border)" />
              <circle cx="32" cy="32" r="26" fill="none" stroke-width="6" stroke-linecap="round" class="stroke-(--ui-text-highlighted) transition-[stroke-dashoffset] duration-700" :stroke-dasharray="RING" :stroke-dashoffset="RING * (1 - setup / 100)" />
            </svg>
            <span class="absolute inset-0 flex items-center justify-center text-sm font-semibold text-highlighted tabular-nums">{{ setup }}%</span>
          </div>
          <div class="flex min-w-0 flex-col gap-1.5">
            <span class="text-sm font-semibold text-highlighted">{{ next ? t('settings.next.title') : t('settings.next.done') }}</span>
            <UButton v-if="next" :label="t(`settings.next.${next.key}`)" :icon="next.icon" :to="next.to" color="neutral" size="sm" trailing-icon="i-lucide-arrow-right" class="w-fit" />
            <UButton :label="t('onboarding.settingsCard.title')" to="/onboarding" color="neutral" variant="link" size="xs" class="w-fit px-0" />
          </div>
        </div>
      </div>

      <!-- Every section, in its group -->
      <section v-for="group in groups" :key="group.key" class="flex flex-col gap-3">
        <h2 class="text-xs font-medium tracking-wide text-muted uppercase">{{ t(`settings.group.${group.key}`) }}</h2>
        <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <template v-for="item in group.items.filter(entry => entry.key !== 'overview')" :key="item.key">
            <NuxtLink v-if="item.to" :to="item.to" class="group flex h-full items-start gap-3 rounded-xl border border-default p-4 transition hover:border-accented hover:shadow-sm focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
              <span class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-elevated"><UIcon :name="item.icon" class="size-4 text-highlighted" /></span>
              <span class="flex min-w-0 flex-1 flex-col gap-1">
                <span class="flex items-center justify-between gap-2">
                  <span class="truncate text-sm font-semibold text-highlighted">{{ label(item) }}</span>
                  <UIcon name="i-lucide-arrow-right" class="size-4 shrink-0 text-dimmed transition group-hover:translate-x-0.5 group-hover:text-highlighted rtl:-scale-x-100" />
                </span>
                <span class="line-clamp-2 text-xs text-muted">{{ description(item) }}</span>
                <span v-if="statusOf(item.key)" class="mt-1 flex items-center gap-1.5 text-xs text-default"><span class="size-1.5 shrink-0 rounded-full" :class="DOT[statusOf(item.key)!.tone]" /><span class="truncate">{{ statusOf(item.key)!.text }}</span></span>
              </span>
            </NuxtLink>
            <div v-else class="flex h-full items-start gap-3 rounded-xl border border-dashed border-default p-4" :aria-disabled="true">
              <span class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-elevated/60"><UIcon :name="item.icon" class="size-4 text-dimmed" /></span>
              <span class="flex min-w-0 flex-1 flex-col gap-1">
                <span class="flex items-center justify-between gap-2">
                  <span class="truncate text-sm font-semibold text-muted">{{ label(item) }}</span>
                  <UBadge :label="t('settings.soon')" color="neutral" variant="soft" size="xs" class="shrink-0 rounded-md" />
                </span>
                <span class="line-clamp-2 text-xs text-muted">{{ description(item) }}</span>
              </span>
            </div>
          </template>
        </div>
      </section>
    </template>
  </SettingsPage>
</template>
