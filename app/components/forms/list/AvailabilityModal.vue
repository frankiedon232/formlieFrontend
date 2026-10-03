<!--
  When a form takes responses (F10, owner 2026-10-03): "Open from" and "Open until" (both optional),
  with quick choices for the end. After the end the link says the form has expired; before the start
  it says when it opens. Saves straight away (PATCH /forms/{id}) — no publishing needed.
-->
<script setup lang="ts">
import type { FormSummary } from '#shared/types/forms'

const props = defineProps<{ form: FormSummary | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [form: FormSummary] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()

/** ISO ↔ the local "YYYY-MM-DDTHH:mm" a datetime-local field uses. */
const toLocal = (iso: string | null) => {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
const toIso = (local: string) => (local ? new Date(local).toISOString() : null)

const opensAt = ref('')
const closesAt = ref('')
watch(
  open,
  value => {
    if (!value || !props.form) return
    opensAt.value = toLocal(props.form.opens_at)
    closesAt.value = toLocal(props.form.closes_at)
  },
  { immediate: true },
)

const DAY = 86_400_000
const presets = computed(() => [
  { label: t('forms.availability.preset.week'), at: () => Date.now() + 7 * DAY },
  { label: t('forms.availability.preset.twoWeeks'), at: () => Date.now() + 14 * DAY },
  { label: t('forms.availability.preset.month'), at: () => Date.now() + 30 * DAY },
  {
    label: t('forms.availability.preset.endOfMonth'),
    at: () => {
      const d = new Date()
      return new Date(d.getFullYear(), d.getMonth() + 1, 0, 23, 59).getTime()
    },
  },
])
function endIn(at: number) {
  const d = new Date(at)
  d.setHours(23, 59, 0, 0)
  closesAt.value = toLocal(d.toISOString())
}

const problem = computed(() => {
  if (opensAt.value && closesAt.value && new Date(closesAt.value) <= new Date(opensAt.value)) return t('forms.availability.endBeforeStart')
  return ''
})
const endsInPast = computed(() => !!closesAt.value && new Date(closesAt.value).getTime() < Date.now())

const { busy, run } = useBusy()
async function save() {
  if (!props.form || problem.value) return
  const updated = await run(async () => {
    try {
      const { data } = await api.patch<FormSummary>(`/forms/${props.form!.id}`, {
        row_version: props.form!.row_version,
        opens_at: toIso(opensAt.value),
        closes_at: toIso(closesAt.value),
      })
      toast.add({ title: t('forms.availability.saved'), icon: 'i-lucide-calendar-check-2', color: 'success' })
      return data
    } catch (error) {
      handle(error)
      return null
    }
  })
  if (updated) {
    emit('saved', updated)
    open.value = false
  }
}
</script>

<template>
  <AppModal v-model:open="open" :title="t('forms.availability.title')" :description="t('forms.availability.desc')" :dismissible="!busy">
    <template #body>
      <form id="availability-form" class="flex flex-col gap-4" @submit.prevent="save">
        <UFormField :label="t('forms.availability.opensAt')" :description="t('forms.availability.opensAtHint')">
          <UInput v-model="opensAt" type="datetime-local" class="w-full" />
        </UFormField>
        <UFormField :label="t('forms.availability.closesAt')" :description="t('forms.availability.closesAtHint')" :error="problem || undefined">
          <UInput v-model="closesAt" type="datetime-local" class="w-full" />
        </UFormField>
        <div class="flex flex-wrap gap-1.5">
          <UButton v-for="preset in presets" :key="preset.label" :label="preset.label" color="neutral" variant="outline" size="xs" @click="endIn(preset.at())" />
          <UButton :label="t('forms.availability.preset.noEnd')" color="neutral" variant="ghost" size="xs" @click="closesAt = ''" />
        </div>
        <UAlert v-if="endsInPast" icon="i-lucide-calendar-x-2" color="warning" variant="subtle" :description="t('forms.availability.pastWarning')" />
      </form>
    </template>
    <template #footer>
      <div class="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" class="justify-center" :disabled="busy" @click="open = false" />
        <UButton type="submit" form="availability-form" :label="t('common.save')" icon="i-lucide-check" color="neutral" class="justify-center" :loading="busy" :disabled="!!problem" />
      </div>
    </template>
  </AppModal>
</template>
