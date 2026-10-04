<script setup lang="ts">
const { t } = useI18n()
const { current, uiLocale } = useAppLocale()

// URLs are the same in every language (no_prefix), so no hreflang alternates, just lang/dir.
useHead({
  htmlAttrs: {
    lang: () => current.value.language,
    dir: () => current.value.dir,
  },
  titleTemplate: title => (title ? `${title} · ${t('app.name')}` : t('app.name')),
})
</script>

<template>
  <UApp :locale="uiLocale">
    <NuxtLoadingIndicator color="var(--ui-primary)" :height="3" />
    <NuxtRouteAnnouncer />
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>
