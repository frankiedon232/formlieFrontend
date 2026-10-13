<script setup lang="ts">
// The Formalie lockup: the Field F glyph in an ink tile and the wordmark in Manrope Bold (docs/brand/BRAND.md).
const { t } = useI18n()
const localePath = useLocalePath()
</script>

<template>
  <NuxtLink
    :to="localePath('/')"
    :aria-label="t('nav.home')"
    class="flex items-center gap-2 rounded-md focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary"
  >
    <span class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-inverted text-inverted">
      <UIcon name="i-formalie-mark" class="size-4" />
    </span>
    <span class="text-lg font-bold tracking-[-0.035em] text-highlighted" dir="ltr">Formalie</span>
  </NuxtLink>
</template>
