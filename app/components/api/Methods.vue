<!-- The HTTP methods an endpoint answers, as small monospace badges in the method colours (GET green, POST violet, PUT amber, DELETE red; owner 2026-10-06); methods it does not answer are struck through. -->
<script setup lang="ts">
import { API_METHODS, type ApiMethod } from '#shared/utils/urls/public'

const props = withDefaults(defineProps<{ methods: ApiMethod[]; all?: boolean; size?: 'xs' | 'sm' }>(), { all: false, size: 'sm' })
const { t } = useI18n()
const shown = computed(() => (props.all ? API_METHODS : API_METHODS.filter(method => props.methods.includes(method))))
</script>

<template>
  <span class="inline-flex flex-nowrap items-center gap-1">
    <UBadge
      v-for="method in shown"
      :key="method"
      :label="method"
      :color="methods.includes(method) ? METHOD_COLOR[method] : 'neutral'"
      :variant="methods.includes(method) ? 'subtle' : 'soft'"
      :size="size"
      class="rounded-md font-mono tracking-tight"
      :class="methods.includes(method) ? METHOD_TEXT[method] : 'text-dimmed line-through'"
    />
    <span v-if="!shown.length" class="text-muted">{{ t('apiService.noMethods') }}</span>
  </span>
</template>
