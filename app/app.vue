<script setup lang="ts">
const { t } = useI18n()
const { uiLocale } = useAppLocale()
const localeHead = useLocaleHead()

useHead({
  htmlAttrs: {
    lang: () => localeHead.value.htmlAttrs.lang,
    dir: () => localeHead.value.htmlAttrs.dir,
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
