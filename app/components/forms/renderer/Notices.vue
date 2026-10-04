<!-- Renderer: notices above the buttons, already registered, exact duplicate, files still uploading. -->
<script setup lang="ts">
defineProps<{ registered: { at?: string } | null; duplicate: boolean; uploadsPending: number }>()
const { t } = useI18n()
const { date } = useFormat()
</script>

<template>
  <UAlert
    v-if="registered"
    icon="i-lucide-user-round-check"
    color="warning"
    variant="subtle"
    :title="t('renderer.identity.registeredTitle')"
    :description="registered.at ? t('renderer.identity.registeredDesc', { date: date(registered.at) }) : t('renderer.identity.registeredDescNoDate')"
  />
  <UAlert v-if="duplicate" icon="i-lucide-copy-x" color="warning" variant="subtle" :title="t('renderer.after.duplicate')" :description="t('renderer.after.duplicateDesc')" />
  <p v-if="uploadsPending" class="flex items-center gap-1.5 text-xs text-toned" role="status" aria-live="polite">
    <UIcon name="i-lucide-loader-circle" class="size-3.5 animate-spin" />{{ t('renderer.files.waiting') }}
  </p>
</template>
