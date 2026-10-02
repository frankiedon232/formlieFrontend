<!-- Status pill (docs/design: soft colour badge). Form statuses map to the sidebar bullet colours. -->
<script setup lang="ts">
import type { BadgeProps } from '@nuxt/ui'

const props = defineProps<{ status: string; label?: string }>()
const { t, te } = useI18n()

const COLORS: Record<string, BadgeProps['color']> = {
  draft: 'warning',
  published: 'success',
  closed: 'secondary',
  archived: 'neutral',
}

const text = computed(
  () => props.label ?? (te(`status.${props.status}`) ? t(`status.${props.status}`) : props.status),
)
</script>

<template>
  <UBadge :label="text" :color="COLORS[status] ?? 'neutral'" variant="subtle" size="sm" class="rounded-md" />
</template>
