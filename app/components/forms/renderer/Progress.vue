<!-- Renderer: "Step 2 of 4 · Contact details" with a percentage and a bar (multi-page forms with the progress bar on). -->
<script setup lang="ts">
defineProps<{ position: number; total: number; page?: string }>()
const { t } = useI18n()
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <div class="flex justify-between text-xs text-muted">
      <span class="min-w-0 truncate">{{ t('builder.page.stepOf', { n: position + 1, total }) }}<template v-if="page?.trim()"> · <span class="text-default">{{ page }}</span></template></span>
      <span>{{ Math.round(((position + 1) / total) * 100) }}%</span>
    </div>
    <UProgress :model-value="position + 1" :max="total" color="neutral" size="xs" />
  </div>
</template>
