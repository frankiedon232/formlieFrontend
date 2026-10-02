<!--
  Date, time, date-time and date range — Nuxt UI all the way: UInputDate / UInputTime (type or
  use the arrow keys per segment) with a UCalendar in a popover. Answers are stored as ISO text:
  `2026-10-02`, `14:30`, `2026-10-02T14:30`, `{ from, to }` — easy to export and compare.
-->
<script setup lang="ts">
import {
  CalendarDate,
  CalendarDateTime,
  type Time,
  parseDate,
  parseDateTime,
  parseTime,
  type DateValue,
} from '@internationalized/date'
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()
const { t } = useI18n()
// Size and style follow the form theme (F8); plain defaults elsewhere.
const control = useControlStyle()
const isWide = useMediaQuery('(min-width: 640px)')

const readonly = computed(() => !!props.field.readonly)
const disabled = computed(() => !!props.field.disabled)
const locked = computed(() => readonly.value || disabled.value)
const open = ref(false)

const attempt = <T,>(parse: () => T): T | undefined => {
  try {
    return parse()
  } catch {
    return undefined
  }
}
const asText = () => (typeof value.value === 'string' ? value.value : '')

// ── Single date / date-time ──────────────────────────────────────────────────────────
const withTime = computed(() => props.field.type === 'datetime')
const date = computed<DateValue | undefined>({
  get: () => {
    const raw = asText()
    if (!raw) return undefined
    return withTime.value ? attempt(() => parseDateTime(raw)) : attempt(() => parseDate(raw.slice(0, 10)))
  },
  set: next => (value.value = next ? next.toString().slice(0, withTime.value ? 16 : 10) : null),
})
/** Picking a day in the calendar keeps the time already typed. */
function pickDay(day: DateValue | undefined) {
  if (!day) return
  const current = date.value
  date.value =
    withTime.value && current && 'hour' in current
      ? new CalendarDateTime(day.year, day.month, day.day, current.hour, current.minute)
      : withTime.value
        ? new CalendarDateTime(day.year, day.month, day.day, 9, 0)
        : new CalendarDate(day.year, day.month, day.day)
  if (!withTime.value) open.value = false
}

// ── Time ─────────────────────────────────────────────────────────────────────────────
const time = computed<Time | undefined>({
  get: () => (asText() ? attempt(() => parseTime(asText())) : undefined),
  set: next => (value.value = next ? next.toString().slice(0, 5) : null),
})

// ── Date range ───────────────────────────────────────────────────────────────────────
type Range = { start: CalendarDate | undefined; end: CalendarDate | undefined }
const range = computed<Range>({
  get: () => {
    const raw = value.value && typeof value.value === 'object' ? (value.value as { from?: string; to?: string }) : {}
    return {
      start: raw.from ? attempt(() => parseDate(raw.from!)) : undefined,
      end: raw.to ? attempt(() => parseDate(raw.to!)) : undefined,
    }
  },
  set: next =>
    (value.value =
      next.start || next.end ? { from: next.start?.toString() ?? '', to: next.end?.toString() ?? '' } : null),
})
const setRange = (next: unknown) => {
  const r = (next ?? {}) as { start?: DateValue; end?: DateValue }
  range.value = {
    start: r.start ? new CalendarDate(r.start.year, r.start.month, r.start.day) : undefined,
    end: r.end ? new CalendarDate(r.end.year, r.end.month, r.end.day) : undefined,
  }
}
</script>

<template>
  <UInputTime
    v-if="field.type === 'time'"
    v-bind="control"
    :id="id"
    v-model="time"
    :disabled="disabled"
    :readonly="readonly"
    :required="field.required"
    icon="i-lucide-clock"
    class="w-full"
  />

  <UInputDate
    v-else-if="field.type === 'date_range'"
    v-bind="control"
    :id="id"
    :model-value="range"
    range
    :disabled="disabled"
    :readonly="readonly"
    :required="field.required"
    icon="i-lucide-calendar-range"
    class="w-full"
    @update:model-value="setRange"
  >
    <template #trailing>
      <UPopover v-model:open="open" :disabled="locked">
        <UButton
          icon="i-lucide-calendar-days"
          color="neutral"
          variant="link"
          size="sm"
          :disabled="locked"
          :aria-label="t('renderer.openCalendar')"
          class="px-0"
        />
        <template #content>
          <UCalendar
            :model-value="range"
            range
            :number-of-months="isWide ? 2 : 1"
            color="neutral"
            class="p-2"
            @update:model-value="setRange"
          />
        </template>
      </UPopover>
    </template>
  </UInputDate>

  <UInputDate
    v-else
    v-bind="control"
    :id="id"
    v-model="date"
    :granularity="withTime ? 'minute' : 'day'"
    :disabled="disabled"
    :readonly="readonly"
    :required="field.required"
    :icon="withTime ? 'i-lucide-calendar-clock' : 'i-lucide-calendar'"
    class="w-full"
  >
    <template #trailing>
      <UPopover v-model:open="open" :disabled="locked">
        <UButton
          icon="i-lucide-calendar-days"
          color="neutral"
          variant="link"
          size="sm"
          :disabled="locked"
          :aria-label="t('renderer.openCalendar')"
          class="px-0"
        />
        <template #content>
          <UCalendar :model-value="date" color="neutral" class="p-2" @update:model-value="v => pickDay(v as DateValue)" />
        </template>
      </UPopover>
    </template>
  </UInputDate>
</template>
