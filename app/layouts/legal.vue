<script setup lang="ts">
// The legal pages' layout (docs/LEGAL-PAGES.md): the site's header and footer around a documentation page. When
// printed or saved as PDF, only the document remains.
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
    <SiteHeader class="print:hidden" />
    <UMain id="main" tabindex="-1">
      <UContainer>
        <slot />
      </UContainer>
    </UMain>
    <SiteFooter class="print:hidden" />
  </div>
</template>
