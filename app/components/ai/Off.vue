<!--
  The assistant is switched off for the workspace (F19): what that means and, for people who manage it,
  the way to switch it on. Every assistant page shows this instead of its content.
-->
<script setup lang="ts">
withDefaults(defineProps<{ size?: 'sm' | 'md' }>(), { size: 'md' })
const { t } = useI18n()
const { can } = useCan()
</script>

<template>
  <AppEmpty
    icon="i-lucide-circle-off"
    :size="size"
    :title="t('ai.off.title')"
    :description="can('ai.settings') ? t('ai.off.descAdmin') : t('ai.off.desc')"
    :actions="can('ai.settings') ? [{ label: t('ai.off.open'), icon: 'i-lucide-sliders-horizontal', color: 'neutral', to: '/ai/settings' }] : undefined"
  />
</template>
