<!-- Temporary body for sections whose roadmap phase hasn't started. -->
<script setup lang="ts">
const props = defineProps<{ icon: string; titleKey: string }>()
const { t } = useI18n()
</script>

<template>
  <UEmpty
    :icon="props.icon"
    :title="t(props.titleKey)"
    :description="t('placeholder.description')"
    :actions="[
      {
        label: t('nav.forms'),
        icon: 'i-lucide-file-text',
        to: '/forms',
        color: 'neutral',
        variant: 'subtle',
      },
    ]"
    class="my-auto"
  />
</template>
