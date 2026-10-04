<!--
  Share → Limits (F10 M3): stop after a number of responses (the link then says the form is full)
  and when the form takes responses (open from / until, the availability window, saved on its own).
-->
<script setup lang="ts">
import type { FormShareSettings, ShareDraft } from '#shared/types/forms'

const props = defineProps<{ settings: FormShareSettings }>()
defineEmits<{ availability: [] }>()
const draft = defineModel<ShareDraft>('draft', { required: true })
const { t } = useI18n()
const { dateTime, number } = useFormat()

const used = computed(() => props.settings.responses_count)
const full = computed(() => draft.value.limitOn && used.value >= draft.value.limit)
const period = computed(() => {
  const { opens_at: from, closes_at: until } = props.settings
  if (from && until) return t('share.limits.between', { from: dateTime(from), until: dateTime(until) })
  if (from) return t('share.limits.from', { from: dateTime(from) })
  if (until) return t('share.limits.until', { until: dateTime(until) })
  return t('share.limits.always')
})
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'p-4 sm:p-5' }">
    <div class="mb-3 flex items-start gap-3">
      <UIcon name="i-lucide-gauge" class="mt-0.5 size-5 shrink-0 text-muted" />
      <div>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('share.limits.title') }}</h2>
        <p class="text-xs text-muted">{{ t('share.limits.desc') }}</p>
      </div>
    </div>

    <div class="flex flex-col gap-3">
      <USwitch v-model="draft.limitOn" :label="t('share.limits.limit')" :description="t('share.limits.limitDesc')" color="neutral" />
      <div v-if="draft.limitOn" class="flex flex-col gap-2 ps-11">
        <UFormField :label="t('share.limits.max')">
          <UInputNumber v-model="draft.limit" :min="2" :max="1000000" :step="1" class="w-44" />
        </UFormField>
        <div class="flex flex-col gap-1">
          <div class="flex justify-between text-xs text-muted">
            <span>{{ t('share.limits.used', { n: number(used), max: number(draft.limit) }) }}</span>
            <span class="tabular-nums">{{ Math.min(100, Math.round((used / Math.max(1, draft.limit)) * 100)) }}%</span>
          </div>
          <UProgress :model-value="Math.min(used, draft.limit)" :max="Math.max(1, draft.limit)" :color="full ? 'warning' : 'neutral'" size="xs" />
          <p v-if="full" class="flex items-center gap-1 text-xs text-warning"><UIcon name="i-lucide-triangle-alert" class="size-3.5" />{{ t('share.limits.full') }}</p>
        </div>
      </div>

      <USeparator />

      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex min-w-0 items-start gap-2">
          <UIcon name="i-lucide-calendar-range" class="mt-0.5 size-4 shrink-0 text-muted" />
          <div class="min-w-0">
            <p class="text-sm font-medium text-highlighted">{{ t('share.limits.when') }}</p>
            <p class="text-xs text-muted">{{ period }}</p>
          </div>
        </div>
        <UButton :label="t('share.limits.change')" icon="i-lucide-calendar-cog" color="neutral" variant="outline" size="xs" @click="$emit('availability')" />
      </div>
    </div>
  </UCard>
</template>
