<!--
  A form's availability at a glance (F10, owner 2026-10-03) — table and grid:
  Always open · Until 12 Oct (amber in the last 3 days) · Opens 5 Oct · Expired 3 Oct.
  Only meaningful for forms that take responses; drafts and closed forms show nothing.
-->
<script setup lang="ts">
import type { FormSummary } from '#shared/types/forms'
import { availabilityOf } from '#shared/utils/forms/availability'

const props = defineProps<{ form: Pick<FormSummary, 'status' | 'opens_at' | 'closes_at'> }>()
const { t } = useI18n()
const { date, dateTime } = useFormat()

const DAY = 86_400_000
const DEEP: Record<string, string> = {
  warning: 'text-(--ui-color-warning-700) dark:text-(--ui-color-warning-300)',
  error: 'text-(--ui-color-error-700) dark:text-(--ui-color-error-300)',
  info: 'text-(--ui-color-info-700) dark:text-(--ui-color-info-300)',
  neutral: 'text-default',
}
const badge = computed(() => {
  if (props.form.status !== 'published') return null
  const state = availabilityOf(props.form)
  switch (state) {
    case 'always':
      return { label: t('forms.availability.always'), icon: 'i-lucide-infinity', color: 'neutral' as const, variant: 'outline' as const, title: '' }
    case 'scheduled':
      return { label: t('forms.availability.opens', { date: date(props.form.opens_at) }), icon: 'i-lucide-calendar-clock', color: 'info' as const, variant: 'subtle' as const, title: dateTime(props.form.opens_at) }
    case 'expired':
      return { label: t('forms.availability.expired', { date: date(props.form.closes_at) }), icon: 'i-lucide-calendar-x-2', color: 'error' as const, variant: 'subtle' as const, title: dateTime(props.form.closes_at) }
    default: {
      if (!props.form.closes_at) return { label: t('forms.availability.from', { date: date(props.form.opens_at) }), icon: 'i-lucide-calendar-check-2', color: 'neutral' as const, variant: 'outline' as const, title: dateTime(props.form.opens_at) }
      const soon = Date.parse(props.form.closes_at) - Date.now() < 3 * DAY
      return {
        label: t('forms.availability.until', { date: date(props.form.closes_at) }),
        icon: 'i-lucide-calendar-range',
        color: soon ? ('warning' as const) : ('neutral' as const),
        variant: soon ? ('subtle' as const) : ('outline' as const),
        title: dateTime(props.form.closes_at),
      }
    }
  }
})
</script>

<template>
  <UBadge v-if="badge" :label="badge.label" :icon="badge.icon" :color="badge.color" :variant="badge.variant" size="sm" :title="badge.title || undefined" class="font-medium whitespace-nowrap" :class="DEEP[badge.color]" />
  <span v-else class="text-dimmed" aria-hidden="true">—</span>
</template>
