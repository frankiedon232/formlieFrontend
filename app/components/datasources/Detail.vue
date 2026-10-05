<!--
  One connection in a panel from the side (F12 M1, detail panel model like a response): header
  with Test now / Edit / Enabled, then facts, settings, permissions and health. "Test now" shows
  the steps live at the top and refreshes the status when done. Floating Previous (K) · position ·
  Next (J). Esc closes.
-->
<script setup lang="ts">
import type { DataSourceDetail } from '#shared/types/datasources'

const props = defineProps<{ id: string | null; ids: string[] }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string]; changed: [] }>()
const { t } = useI18n()
const api = useApi()
const confirm = useConfirm()
const { handle } = useErrorHandler()

const source = ref<DataSourceDetail | null>(null)
const loading = ref(false)
const failed = ref(false)
async function load(id: string) {
  loading.value = true
  failed.value = false
  try {
    source.value = (await api.get<DataSourceDetail>(`/datasources/${id}`)).data
  } catch (error) {
    failed.value = true
    handle(error)
  } finally {
    loading.value = false
  }
}
const runner = useConnectionTest()
watch(
  () => [props.id, open.value] as const,
  ([id, isOpen]) => {
    if (!id || !isOpen) return
    runner.reset()
    void load(id)
  },
  { immediate: true },
)

const index = computed(() => (props.id ? props.ids.indexOf(props.id) : -1))
const prev = computed(() => (index.value > 0 ? props.ids[index.value - 1] : null))
const next = computed(() => (index.value >= 0 && index.value < props.ids.length - 1 ? props.ids[index.value + 1] : null))
defineShortcuts({
  j: { usingInput: false, handler: () => open.value && next.value && emit('go', next.value) },
  k: { usingInput: false, handler: () => open.value && prev.value && emit('go', prev.value) },
})

async function testNow() {
  if (!source.value) return
  const id = source.value.id
  const result = await runner.start({ savedId: id })
  if (result && source.value?.id === id) {
    await load(id)
    emit('changed')
  }
}

const { busy, run } = useBusy()
async function setEnabled(enabled: boolean) {
  if (!source.value) return
  if (!enabled && !(await confirm({ title: t('dataSources.disable.title', { name: source.value.name }), description: t('dataSources.disable.desc'), confirmLabel: t('dataSources.disable.confirm') }))) return
  const id = source.value.id
  await run(
    async () => {
      const { data } = await api.patch<DataSourceDetail>(`/datasources/${id}`, { enabled })
      if (source.value?.id === id) source.value = data
      emit('changed')
    },
    { success: enabled ? t('dataSources.toast.enabled') : t('dataSources.toast.disabled') },
  )
}
async function duplicate() {
  if (!source.value) return
  const id = source.value.id
  await run(
    async () => {
      const { data } = await api.post<DataSourceDetail>(`/datasources/${id}/duplicate`)
      emit('changed')
      await navigateTo(`/data-sources/connections/${data.id}/edit`)
    },
    { success: t('dataSources.toast.duplicated') },
  )
}
async function remove() {
  if (!source.value || !(await confirm({ title: t('dataSources.delete.title', { name: source.value.name }), description: t('dataSources.delete.desc'), confirmLabel: t('dataSources.delete.confirm'), danger: true }))) return
  const id = source.value.id
  await run(
    async () => {
      await api.del(`/datasources/${id}`)
      emit('changed')
      if (next.value) emit('go', next.value)
      else if (prev.value) emit('go', prev.value)
      else open.value = false
    },
    { success: t('dataSources.toast.deleted') },
  )
}
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="source?.name || t('nav.dataConnections')"
    :ui="{ content: 'w-full sm:max-w-2xl', header: 'border-b-0 pb-2', body: 'flex flex-col gap-5 pb-56', footer: 'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4' }"
  >
    <template #header>
      <div v-if="!source" class="flex w-full items-center gap-3.5">
        <USkeleton class="size-16 rounded-2xl" />
        <div class="flex flex-1 flex-col gap-2"><USkeleton class="h-5 w-48" /><USkeleton class="h-4 w-32" /></div>
      </div>
      <DatasourcesDetailHeader v-else :source="source" :busy="busy" :testing="runner.starting.value || runner.running.value" @test="testNow" @enabled="setEnabled" @duplicate="duplicate" @delete="remove" @close="open = false" />
    </template>

    <template #body>
      <div v-if="loading && !source" class="flex flex-col gap-4" :aria-label="t('common.loading')">
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3"><USkeleton v-for="n in 6" :key="n" class="h-14 rounded-lg" /></div>
        <USkeleton v-for="n in 4" :key="n" class="h-16 w-full rounded-lg" />
      </div>
      <UEmpty v-else-if="failed && !source" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" variant="naked" />
      <div v-else-if="source" class="flex flex-col gap-5 transition-opacity" :class="loading || busy ? 'opacity-60' : ''" :aria-busy="loading || busy || undefined">
        <div v-if="runner.test.value || runner.starting.value" class="rounded-lg border border-default p-3 sm:p-4">
          <DatasourcesTestProgress :test="runner.test.value" :starting="runner.starting.value" />
        </div>
        <DatasourcesDetailBody :source="source" />
      </div>
    </template>

    <template #footer>
      <nav class="pointer-events-auto flex items-center gap-1 rounded-full border border-default bg-default/95 p-1 shadow-lg backdrop-blur" :aria-label="t('dataSources.detail.navigate')">
        <UButton :label="t('responses.detail.prevShort')" icon="i-lucide-arrow-up" color="neutral" variant="ghost" size="sm" class="rounded-full" :disabled="!prev" :aria-label="t('dataSources.detail.previous')" @click="prev && emit('go', prev)">
          <template #trailing><UKbd value="K" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
        <span v-if="index >= 0" class="px-2 text-xs text-muted tabular-nums">{{ t('responses.detail.position', { n: index + 1, total: ids.length }) }}</span>
        <UButton :label="t('responses.detail.nextShort')" icon="i-lucide-arrow-down" color="neutral" variant="solid" size="sm" class="rounded-full" :disabled="!next" :aria-label="t('dataSources.detail.next')" @click="next && emit('go', next)">
          <template #trailing><UKbd value="J" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
      </nav>
    </template>
  </USlideover>
</template>
