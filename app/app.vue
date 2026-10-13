<script setup lang="ts">
import * as uiLocales from '@nuxt/ui/locale'

const { locale } = useI18n()
const head = useLocaleHead()

// Nuxt UI's own strings (close buttons, pagination …) in the page's language where it has them.
const uiLocale = computed(() => {
  const entry = SITE_LOCALES.find(item => item.code === locale.value)
  const key = (entry?.uiLocale ?? 'en') as keyof typeof uiLocales
  return uiLocales[key] ?? uiLocales.en
})

useHead({
  htmlAttrs: {
    lang: () => head.value.htmlAttrs.lang,
    dir: () => head.value.htmlAttrs.dir,
  },
  link: () => head.value.link,
  meta: () => head.value.meta,
})
</script>

<template>
  <UApp :locale="uiLocale">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>
