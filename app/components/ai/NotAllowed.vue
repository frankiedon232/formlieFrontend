<!--
  The workspace hasn't let the assistant read what this page needs (F19, AI settings → What it may read):
  says which part, and for people who manage the assistant, the way to change it.
-->
<script setup lang="ts">
import type { AiSource } from '#shared/types/ai'

defineProps<{ source: AiSource }>()
const { t } = useI18n()
const { can } = useCan()
</script>

<template>
  <AppEmpty
    icon="i-lucide-eye-off"
    :title="t('ai.notAllowed.title', { part: t(`ai.source.${source}.label`) })"
    :description="can('ai.settings') ? t('ai.notAllowed.descAdmin') : t('ai.notAllowed.desc')"
    :actions="can('ai.settings') ? [{ label: t('ai.off.open'), icon: 'i-lucide-sliders-horizontal', color: 'neutral', to: '/ai/settings' }] : undefined"
  />
</template>
