<script setup lang="ts">
// The 20 language names in their own scripts, scrolling slowly (UMarquee stops for reduced motion).
const { t } = useI18n()
const locales = SITE_LOCALES
</script>

<template>
  <UPageSection :title="t('home.languages.title')" :description="t('home.languages.description')">
    <UMarquee pause-on-hover :overlay="true" :ui="{ root: '[--duration:50s] [--gap:--spacing(3)]' }">
      <span
        v-for="item in locales"
        :key="item.code"
        :lang="item.language"
        class="flex items-center gap-2 rounded-full bg-default px-4 py-2 text-sm font-medium whitespace-nowrap text-highlighted ring-1 ring-default"
      >
        <UIcon :name="item.flag" class="size-5" />
        {{ item.name }}
      </span>
    </UMarquee>
  </UPageSection>
</template>
