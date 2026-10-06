<!-- The HTTP methods an endpoint answers, as small monospace outline badges (monochrome, rule 21). -->
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
      color="neutral"
      :variant="methods.includes(method) ? 'outline' : 'soft'"
      :size="size"
      class="rounded-md font-mono tracking-tight"
      :class="methods.includes(method) ? 'text-highlighted' : 'text-dimmed line-through'"
    />
    <span v-if="!shown.length" class="text-muted">{{ t('apiService.noMethods') }}</span>
  </span>
</template>
