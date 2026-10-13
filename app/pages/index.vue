<script setup lang="ts">
// S0 placeholder: proves the stack (Nuxt UI, the theme, Manrope, the 20 languages). The home page arrives in S2.
const { t } = useI18n()

useSeoMeta({
  title: () => `${t('site.name')} · ${t('site.tagline')}`,
  description: () => t('site.description'),
})
</script>

<template>
  <UPageHero :title="t('site.tagline')" :description="t('site.description')">
    <template #top>
      <div class="flex justify-center pt-16">
        <span class="flex size-12 items-center justify-center rounded-xl bg-inverted text-inverted">
          <UIcon name="i-formalie-mark" class="size-6" />
        </span>
      </div>
    </template>
    <template #footer>
      <p class="text-center text-sm text-muted">{{ t('placeholder.building') }}</p>
    </template>
  </UPageHero>
</template>
