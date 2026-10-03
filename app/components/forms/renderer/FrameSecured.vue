<!-- "Encrypted · Secured by Formalie" — the trust line on public form pages. -->
<script setup lang="ts">
const { t } = useI18n()
</script>

<template>
  <i18n-t keypath="public.frame.secured" tag="p" scope="global" class="inline-flex items-center gap-1.5">
    <template #icon
      ><UIcon
        name="i-lucide-shield-check"
        class="size-3.5 shrink-0"
        :aria-label="t('public.frame.encrypted')"
    /></template>
    <template #brand><span class="font-semibold">Formalie</span></template>
  </i18n-t>
</template>
