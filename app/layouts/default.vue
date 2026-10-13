<script setup lang="ts">
const { t } = useI18n()
</script>

<template>
  <div>
    <a
      href="#main"
      class="sr-only rounded-md bg-inverted text-sm text-inverted focus:not-sr-only focus:fixed focus:start-4 focus:top-4 focus:z-[100] focus:px-4 focus:py-2"
    >
      {{ t('site.skipToContent') }}
    </a>
    <SiteHeader />
    <UMain id="main" tabindex="-1">
      <slot />
    </UMain>
    <SiteFooter />
  </div>
</template>
