<!-- Renderer: Back and Next / Submit, in the form's button style (themed colour, style, full width). -->
<script setup lang="ts">
defineProps<{
  canGoBack: boolean
  last: boolean
  submitting: boolean
  uploadsPending: number
  button: { color: 'primary' | 'neutral'; variant: 'solid' | 'outline' | 'soft'; block: boolean; class: string }
}>()
const emit = defineEmits<{ back: [] }>()
const { t } = useI18n()
</script>

<template>
  <div class="flex items-center gap-2 pt-2" :class="button.block ? 'flex-col-reverse' : 'justify-between'">
    <UButton
      v-if="canGoBack"
      :label="t('common.back')"
      icon="i-lucide-arrow-left"
      :color="button.color"
      variant="ghost"
      :block="button.block"
      :class="button.class"
      class="rtl:[&_svg]:rotate-180"
      @click="emit('back')"
    />
    <span v-else-if="!button.block" />
    <UButton
      type="submit"
      :loading="submitting"
      :disabled="uploadsPending > 0"
      :label="last ? t('renderer.submit') : t('renderer.next')"
      :trailing-icon="last ? undefined : 'i-lucide-arrow-right'"
      :color="button.color"
      :variant="button.variant"
      :block="button.block"
      :class="button.class"
      class="rtl:[&_svg]:rotate-180"
    />
  </div>
</template>
