<!--
  Responses | Insights (F11, owner 2026-10-04): the page's two views, at the start of the list's
  toolbar line (and on top of Insights), so the switch and the table controls share one line.
-->
<script setup lang="ts">
const view = defineModel<'responses' | 'insights'>({ required: true })
const { t } = useI18n()
const items = computed(() => [
  { value: 'responses', label: t('responses.tabs.responses'), icon: 'i-lucide-table-2' },
  { value: 'insights', label: t('responses.tabs.summary'), icon: 'i-lucide-chart-no-axes-combined' },
])
</script>

<template>
  <UTabs v-model="view" :items="items" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" :aria-label="t('responses.tabs.label')" />
</template>
