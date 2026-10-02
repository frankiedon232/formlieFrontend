<!--
  Date range filter: presets + two-month calendar (one month on phones). Emits ISO dates
  (YYYY-MM-DD) or empty strings for "any time".
-->
<script setup lang="ts">
import {
  type CalendarDate,
  endOfMonth,
  getLocalTimeZone,
  parseDate,
  startOfMonth,
  startOfYear,
  today,
} from '@internationalized/date'

const props = defineProps<{ from: string; to: string }>()
const emit = defineEmits<{ change: [from: string, to: string] }>()

const { t } = useI18n()
const { date } = useFormat()
const isWide = useMediaQuery('(min-width: 640px)')
const open = ref(false)

const toIso = (value: CalendarDate) => value.toString()
const safeParse = (value: string) => {
  try {
    return value ? parseDate(value) : undefined
  } catch {
    return undefined
  }
}

const range = shallowRef<{ start: CalendarDate | undefined; end: CalendarDate | undefined }>({
  start: safeParse(props.from),
  end: safeParse(props.to),
})
watch(
  () => [props.from, props.to],
  () => {
    range.value = { start: safeParse(props.from), end: safeParse(props.to) }
  },
)

const label = computed(() => {
  if (!props.from && !props.to) return t('dataView.anyTime')
  if (props.from === props.to) return date(props.from)
  return `${props.from ? date(props.from) : '…'} – ${props.to ? date(props.to) : '…'}`
})

const presets = computed(() => {
  const now = today(getLocalTimeZone())
  return [
    { label: t('dataView.today'), start: now, end: now },
    { label: t('dataView.last7'), start: now.subtract({ days: 6 }), end: now },
    { label: t('dataView.last30'), start: now.subtract({ days: 29 }), end: now },
    { label: t('dataView.thisMonth'), start: startOfMonth(now), end: endOfMonth(now) },
    { label: t('dataView.thisYear'), start: startOfYear(now), end: now },
  ]
})

function apply(start?: CalendarDate, end?: CalendarDate) {
  emit('change', start ? toIso(start) : '', end ? toIso(end ?? start!) : start ? toIso(start) : '')
  open.value = false
}

function onCalendar(value: unknown) {
  const next = value as { start?: CalendarDate; end?: CalendarDate } | null
  range.value = { start: next?.start, end: next?.end }
  if (next?.start && next?.end) apply(next.start, next.end)
}
</script>

<template>
  <UPopover v-model:open="open" :content="{ align: 'end' }">
    <UButton
      icon="i-lucide-calendar"
      :label="label"
      color="neutral"
      variant="outline"
      :class="from || to ? 'text-highlighted' : ''"
    />

    <template #content>
      <div class="flex flex-col sm:flex-row">
        <div
          class="flex flex-row flex-wrap gap-1 border-b border-default p-2 sm:flex-col sm:border-e sm:border-b-0"
        >
          <UButton
            v-for="preset in presets"
            :key="preset.label"
            :label="preset.label"
            color="neutral"
            variant="ghost"
            size="sm"
            class="justify-start"
            @click="apply(preset.start, preset.end)"
          />
          <UButton
            :label="t('dataView.anyTime')"
            color="neutral"
            variant="ghost"
            size="sm"
            class="justify-start"
            @click="apply()"
          />
        </div>
        <UCalendar
          :model-value="range"
          range
          :number-of-months="isWide ? 2 : 1"
          class="p-2"
          @update:model-value="onCalendar"
        />
      </div>
    </template>
  </UPopover>
</template>
