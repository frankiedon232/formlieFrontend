<!--
  Send earlier responses (F12 M2): responses submitted before the form started storing in the
  database are sent in the background for a date range, with progress on the destination's panel.
  Rows are written the same way as new ones; nothing already sent is sent twice.
-->
<script setup lang="ts">
import type { DestinationDetail } from '#shared/types/destinations'

const props = defineProps<{ destination: DestinationDetail | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ started: [destination: DestinationDetail] }>()
const { t } = useI18n()
const api = useApi()
const { number, date } = useFormat()
const { busy, run } = useBusy()

const day = (time: number) => new Date(time).toISOString().slice(0, 10)
const from = ref('')
const to = ref('')
watch(open, value => {
  if (!value || !props.destination) return
  const covers = Date.parse(props.destination.covers_from)
  to.value = day(covers)
  from.value = day(covers - 365 * 86_400_000)
})
const invalid = computed(() => !from.value || !to.value || from.value > to.value)

async function start() {
  if (!props.destination || invalid.value) return
  const id = props.destination.id
  const result = await run(() => api.post<DestinationDetail>(`/destinations/${id}/backfill`, { from: from.value, to: to.value }), { success: t('destinations.backfill.started') })
  if (!result) return
  emit('started', result.data)
  open.value = false
}
</script>

<template>
  <AppModal v-model:open="open" :title="t('destinations.backfill.title')" :description="t('destinations.backfill.desc')" :dismissible="!busy">
    <template #body>
      <form id="backfill-form" class="flex flex-col gap-4" @submit.prevent="start">
        <p v-if="destination" class="rounded-lg border border-default px-3 py-2 text-sm text-default">
          {{ t('destinations.backfill.notSent', { n: number(destination.not_sent), date: date(destination.covers_from) }, destination.not_sent) }}
        </p>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <UFormField :label="t('destinations.backfill.from')" required>
            <UInput v-model="from" type="date" class="w-full" :max="to || undefined" />
          </UFormField>
          <UFormField :label="t('destinations.backfill.to')" required :error="from && to && from > to ? t('destinations.backfill.order') : undefined">
            <UInput v-model="to" type="date" class="w-full" :min="from || undefined" />
          </UFormField>
        </div>
        <p class="flex gap-1.5 text-xs text-muted">
          <UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" />
          {{ t('destinations.backfill.note') }}
        </p>
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" :disabled="busy" @click="open = false" />
        <UButton type="submit" form="backfill-form" :label="t('destinations.backfill.start')" icon="i-lucide-history" color="neutral" :loading="busy" :disabled="invalid || !destination?.not_sent" />
      </div>
    </template>
  </AppModal>
</template>
