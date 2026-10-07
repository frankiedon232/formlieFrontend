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
// Settings → Privacy and data (F14 M5): a consent line above Submit, with the organisation's notice
const privacy = useState<{ notice_url: string | null; consent: boolean; consent_text: string | null; org: string } | null>('public:privacy', () => null)
const consent = computed(() => (privacy.value?.consent ? (privacy.value.consent_text || t('renderer.consentLine', { org: privacy.value.org })) : null))
</script>

<template>
  <p v-if="last && consent" class="flex items-start gap-1.5 pt-2 text-xs text-(--ui-text-muted)">
    <UIcon name="i-lucide-shield-check" class="mt-0.5 size-3.5 shrink-0" />
    <span>{{ consent }}<template v-if="privacy?.notice_url"> <FormsRendererFrameLink :href="privacy.notice_url" :title="t('renderer.privacyNotice')" class="font-medium text-(--ui-text) underline underline-offset-2">{{ t('renderer.privacyNotice') }}</FormsRendererFrameLink></template></span>
  </p>
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
