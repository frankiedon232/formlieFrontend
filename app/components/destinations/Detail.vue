<!--
  A form's response storage in a panel from the side (F12 M2, detail panel model): header with
  Delivering on / off, Send earlier responses and Retry failed, then progress, facts, deliveries,
  columns and new fields. While earlier responses are being sent, it refreshes every second.
  Previous (K) · position · Next (J). Esc closes. `backfill` opens Send earlier responses at once
  (right after setting up).
-->
<script setup lang="ts">
import type { DestinationDetail } from '#shared/types/destinations'

const props = defineProps<{ id: string | null; ids: string[]; backfill?: boolean }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string]; changed: [] }>()
const { t } = useI18n()
const api = useApi()
const confirm = useConfirm()
const { handle } = useErrorHandler()

const destination = ref<DestinationDetail | null>(null)
const loading = ref(false)
const failed = ref(false)
const refreshKey = ref(0)
async function load(id: string, quiet = false) {
  if (!quiet) loading.value = true
  failed.value = false
  try {
    destination.value = (await api.get<DestinationDetail>(`/destinations/${id}`, undefined, { background: quiet })).data
    if (!quiet) refreshKey.value++
  } catch (error) {
    failed.value = true
    if (!quiet) handle(error)
  } finally {
    loading.value = false
  }
}
const backfillOpen = ref(false)
watch(
  () => [props.id, open.value] as const,
  async ([id, isOpen]) => {
    if (!id || !isOpen) return
    await load(id)
    if (props.backfill && destination.value?.not_sent) backfillOpen.value = true
  },
  { immediate: true },
)
// Follow earlier responses being sent.
const { pause, resume } = useIntervalFn(() => props.id && open.value && void load(props.id, true), 1000, { immediate: false })
watch(() => destination.value?.backfill?.status, status => {
  if (status === 'running') resume()
  else {
    pause()
    refreshKey.value++
  }
})

const index = computed(() => (props.id ? props.ids.indexOf(props.id) : -1))
const prev = computed(() => (index.value > 0 ? props.ids[index.value - 1] : null))
const next = computed(() => (index.value >= 0 && index.value < props.ids.length - 1 ? props.ids[index.value + 1] : null))
defineShortcuts({
  j: { usingInput: false, handler: () => open.value && next.value && emit('go', next.value) },
  k: { usingInput: false, handler: () => open.value && prev.value && emit('go', prev.value) },
})

const { busy, run } = useBusy()
async function change(work: () => Promise<{ data: DestinationDetail } | unknown>, success: string) {
  const id = destination.value?.id
  if (!id) return
  await run(
    async () => {
      const result = await work()
      if (result && typeof result === 'object' && 'data' in result && destination.value?.id === id) destination.value = (result as { data: DestinationDetail }).data
      else await load(id, true)
      refreshKey.value++
      emit('changed')
    },
    { success },
  )
}
const pauseResume = (paused: boolean) => change(() => api.patch<DestinationDetail>(`/destinations/${destination.value!.id}`, { paused }), paused ? t('destinations.toast.paused') : t('destinations.toast.resumed'))
const retryAll = () => change(() => api.post(`/destinations/${destination.value!.id}/retry`, {}), t('destinations.toast.retried', { n: destination.value!.failed }, destination.value!.failed))
const addColumns = (keys: string[]) => change(() => api.post<DestinationDetail>(`/destinations/${destination.value!.id}/columns`, { keys }), t('destinations.toast.columnsAdded', { n: keys.length }, keys.length))
async function remove() {
  if (!destination.value) return
  const name = destination.value.form.name
  if (!(await confirm({ title: t('destinations.remove.title', { form: name }), description: t('destinations.remove.desc'), confirmLabel: t('destinations.remove.confirm'), danger: true }))) return
  const id = destination.value.id
  await run(
    async () => {
      await api.del(`/destinations/${id}`)
      emit('changed')
      open.value = false
    },
    { success: t('destinations.toast.removed') },
  )
}
function started(result: DestinationDetail) {
  destination.value = result
  emit('changed')
}
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="destination?.form.name || t('nav.destinations')"
    :ui="{ content: 'w-full sm:max-w-2xl', header: 'border-b-0 pb-2', body: 'flex flex-col gap-5 pb-56', footer: 'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4' }"
  >
    <template #header>
      <div v-if="!destination" class="flex w-full items-center gap-3.5">
        <USkeleton class="size-16 rounded-2xl" />
        <div class="flex flex-1 flex-col gap-2"><USkeleton class="h-5 w-48" /><USkeleton class="h-4 w-32" /></div>
      </div>
      <DestinationsDetailHeader v-else :destination="destination" :busy="busy" @pause="pauseResume" @backfill="backfillOpen = true" @retry="retryAll" @remove="remove" @close="open = false" />
    </template>

    <template #body>
      <div v-if="loading && !destination" class="flex flex-col gap-4" :aria-label="t('common.loading')">
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3"><USkeleton v-for="n in 6" :key="n" class="h-14 rounded-lg" /></div>
        <USkeleton v-for="n in 4" :key="n" class="h-14 w-full rounded-lg" />
      </div>
      <AppEmpty v-else-if="failed && !destination" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" variant="naked" />
      <div v-else-if="destination" class="transition-opacity" :class="loading || busy ? 'opacity-60' : ''" :aria-busy="loading || busy || undefined">
        <DestinationsDetailBody :destination="destination" :refresh-key="refreshKey" :busy="busy" @add-columns="addColumns" @retried="() => id && load(id, true)" />
      </div>
      <DestinationsBackfillModal v-model:open="backfillOpen" :destination="destination" @started="started" />
    </template>

    <template #footer>
      <nav class="pointer-events-auto flex items-center gap-1 rounded-full border border-default bg-default/95 p-1 shadow-lg backdrop-blur" :aria-label="t('destinations.detail.navigate')">
        <UButton :label="t('responses.detail.prevShort')" icon="i-lucide-arrow-up" color="neutral" variant="ghost" size="sm" class="rounded-full" :disabled="!prev" :aria-label="t('destinations.detail.previous')" @click="prev && emit('go', prev)">
          <template #trailing><UKbd value="K" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
        <span v-if="index >= 0" class="px-2 text-xs text-muted tabular-nums">{{ t('responses.detail.position', { n: index + 1, total: ids.length }) }}</span>
        <UButton :label="t('responses.detail.nextShort')" icon="i-lucide-arrow-down" color="neutral" variant="solid" size="sm" class="rounded-full" :disabled="!next" :aria-label="t('destinations.detail.next')" @click="next && emit('go', next)">
          <template #trailing><UKbd value="J" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
      </nav>
    </template>
  </USlideover>
</template>
