<script setup lang="ts">
const { t } = useI18n()
const { current, uiLocale } = useAppLocale()
const tenant = useTenant()
// The workspace's own tab icon (Settings → Branding, F14), else its logo, else Formalie's
const tabIcon = computed(() => (tenant.profile.value?.mode === 'tenant' ? (tenant.profile.value.favicon_url ?? tenant.profile.value.logo_url) : null) ?? null)

// URLs are the same in every language (no_prefix), so no hreflang alternates, just lang/dir.
useHead({
  htmlAttrs: {
    lang: () => current.value.language,
    dir: () => current.value.dir,
  },
  titleTemplate: title => (title ? `${title} · ${t('app.name')}` : t('app.name')),
  // Same keys as Formalie's icons in nuxt.config, so the workspace's icon replaces both instead of competing
  link: () =>
    tabIcon.value
      ? [
          { key: 'icon-ico', rel: 'icon', href: tabIcon.value },
          { key: 'icon-svg', rel: 'icon', href: tabIcon.value },
        ]
      : [],
})
</script>

<template>
  <UApp :locale="uiLocale">
    <NuxtLoadingIndicator color="var(--ui-primary)" :height="3" />
    <NuxtRouteAnnouncer />
    <!-- The app's own right-click menu everywhere in the portal (never the browser's) -->
    <AppContextMenu>
      <NuxtLayout>
        <NuxtPage />
      </NuxtLayout>
    </AppContextMenu>
  </UApp>
</template>
