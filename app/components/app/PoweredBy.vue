<!--
  "Powered by Formalie" with the Formalie mark (owner, 2026-10-07: whatever a workspace brands, Formalie
  is always present). On the workspace sign-in page and its preview; links to Formalie's website.
  `tone="light"` for dark panels (the showcase).
-->
<script setup lang="ts">
withDefaults(defineProps<{ tone?: 'default' | 'light'; size?: 'sm' | 'xs' }>(), { tone: 'default', size: 'sm' })
const { t } = useI18n()
</script>

<template>
  <a
    href="https://formalie.com"
    target="_blank"
    rel="noopener"
    class="inline-flex shrink-0 items-center gap-1.5 rounded-full focus-visible:outline-2 focus-visible:outline-offset-2"
    :class="[tone === 'light' ? 'text-white/75 hover:text-white focus-visible:outline-white' : 'text-muted hover:text-highlighted focus-visible:outline-(--ui-border-inverted)', size === 'xs' ? 'text-[10px]' : 'text-xs']"
    :aria-label="t('app.poweredBy', { brand: 'Formalie' })"
  >
    <span class="flex shrink-0 items-center justify-center rounded-md" :class="[tone === 'light' ? 'bg-white text-neutral-950' : 'bg-inverted text-inverted', size === 'xs' ? 'size-3.5' : 'size-5']">
      <UIcon name="i-lucide-file-check-2" :class="size === 'xs' ? 'size-2.5' : 'size-3'" />
    </span>
    <i18n-t keypath="app.poweredBy" tag="span" scope="global">
      <template #brand><span class="font-semibold" :class="tone === 'light' ? 'text-white' : 'text-highlighted'">Formalie</span></template>
    </i18n-t>
  </a>
</template>
