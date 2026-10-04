<!--
  Page editor controls (Resources → Pages): the designer's own Page group (style drawn as small
  pictures, tone, website link, quick facts) and its Background group (colour, gradient or image),
  the two parts a page design holds. Works on the sample form provided by the page editor.
-->
<script setup lang="ts">
const { t } = useI18n()
</script>

<template>
  <div class="flex flex-col gap-5">
    <section class="flex flex-col gap-3">
      <h3 class="flex items-center gap-1.5 text-xs font-medium text-muted uppercase"><UIcon name="i-lucide-app-window" class="size-3.5" />{{ t('designer.group.frame') }}</h3>
      <FormsDesignerPanelFrame />
    </section>
    <section class="flex flex-col gap-3 border-t border-default pt-4">
      <h3 class="flex items-center gap-1.5 text-xs font-medium text-muted uppercase"><UIcon name="i-lucide-paint-bucket" class="size-3.5" />{{ t('designer.group.background') }}</h3>
      <FormsDesignerPanelLayout group="background" />
    </section>
  </div>
</template>
