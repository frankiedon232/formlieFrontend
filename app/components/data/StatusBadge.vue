<!-- Status pill (docs/design: soft colour badge). Form statuses map to the sidebar bullet colours; response review statuses (F11) too. -->
<script setup lang="ts">
import type { BadgeProps } from '@nuxt/ui'

const props = defineProps<{ status: string; label?: string }>()
const { t, te } = useI18n()

const COLORS: Record<string, BadgeProps['color']> = {
  draft: 'warning',
  published: 'success',
  closed: 'secondary',
  archived: 'neutral',
  // Responses (F11): review status.
  new: 'neutral',
  reviewed: 'warning',
  approved: 'success',
  rejected: 'error',
  // Exports (F11 M3): the file's state.
  queued: 'warning',
  running: 'warning',
  ready: 'success',
  expired: 'neutral',
  failed: 'error',
  // Data sources (F12): the connection's health.
  connected: 'success',
  attention: 'warning',
  failing: 'error',
  disabled: 'neutral',
  untested: 'secondary',
  // Response storage (F12 M2): a destination and its deliveries.
  active: 'success',
  paused: 'neutral',
  sent: 'success',
  pending: 'warning',
  held: 'neutral',
  not_sent: 'neutral',
  // API tokens (F13 M2)
  expiring: 'warning',
  revoked: 'error',
  // Webhook deliveries (F13 M6)
  delivered: 'success',
  retrying: 'warning',
}

// Deeper text than Nuxt UI's subtle default (500 shade), so status reads crisply (owner, 2026-10-03; docs/design).
const TEXT: Record<string, string> = {
  warning: 'text-(--ui-color-warning-700) dark:text-(--ui-color-warning-300)',
  success: 'text-(--ui-color-success-700) dark:text-(--ui-color-success-300)',
  secondary: 'text-(--ui-color-secondary-700) dark:text-(--ui-color-secondary-300)',
  error: 'text-(--ui-color-error-700) dark:text-(--ui-color-error-300)',
  info: 'text-(--ui-color-info-700) dark:text-(--ui-color-info-300)',
  neutral: 'text-default',
}
const color = computed(() => COLORS[props.status] ?? 'neutral')

const text = computed(
  () => props.label ?? (te(`status.${props.status}`) ? t(`status.${props.status}`) : props.status),
)
</script>

<template>
  <UBadge :label="text" :color="color" variant="subtle" size="sm" class="rounded-md font-medium" :class="TEXT[color ?? 'neutral']" />
</template>
