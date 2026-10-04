<!--
  One response, in a rich panel from the side (F11, owner 2026-10-04: "super rich", next / previous
  floating in the footer). Header: avatar, who, number, form, status, one-click review bar, menu.
  Body: facts as tiles, tags, a possible-duplicate notice, every answer in a card per page, notes
  and history. A possible duplicate can be opened, cleared ("Not a duplicate") or rejected (status
  Rejected + tag "duplicate"). Footer: a floating pill with Previous (K) · "3 / 20" · Next (J). Esc closes.
-->
<script setup lang="ts">
import type { ResponseDetail, ResponseStatus } from '#shared/types/responses'

const props = defineProps<{ id: string | null; ids: string[] }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string]; changed: [] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const confirm = useConfirm()
const toast = useToast()

const response = ref<ResponseDetail | null>(null)
const loading = ref(false)
const failed = ref(false)
async function load(id: string) {
  loading.value = true
  failed.value = false
  try {
    response.value = (await api.get<ResponseDetail>(`/responses/${id}`)).data
  } catch (error) {
    failed.value = true
    handle(error)
  } finally {
    loading.value = false
  }
}
watch(() => [props.id, open.value] as const, ([id, isOpen]) => id && isOpen && void load(id), { immediate: true })

const index = computed(() => (props.id ? props.ids.indexOf(props.id) : -1))
const prev = computed(() => (index.value > 0 ? props.ids[index.value - 1] : null))
const next = computed(() => (index.value >= 0 && index.value < props.ids.length - 1 ? props.ids[index.value + 1] : null))
defineShortcuts({
  j: { usingInput: false, handler: () => open.value && next.value && emit('go', next.value) },
  k: { usingInput: false, handler: () => open.value && prev.value && emit('go', prev.value) },
})

// Status and tags: saved at once, one change at a time.
const { busy, run } = useBusy()
async function save(body: { status?: ResponseStatus; tags?: string[]; duplicate?: 'cleared' }) {
  if (!response.value) return
  const id = response.value.id
  await run(async () => {
    const { data } = await api.patch<ResponseDetail>(`/responses/${id}`, body)
    if (response.value?.id === id) response.value = data
    emit('changed')
  })
}
async function remove() {
  if (!response.value || !(await confirm({ title: t('responses.delete.title', { n: 1 }, 1), description: t('responses.delete.desc'), danger: true }))) return
  const id = response.value.id
  await run(async () => {
    await api.del(`/responses/${id}`)
    toast.add({ title: t('responses.toast.deleted', { n: 1 }, 1), color: 'success', icon: 'i-lucide-circle-check' })
    emit('changed')
    if (next.value) emit('go', next.value)
    else if (prev.value) emit('go', prev.value)
    else open.value = false
  })
}
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="response?.respondent.name || response?.respondent.email || t('responses.crumb')"
    :ui="{ content: 'w-full sm:max-w-2xl', header: 'border-b-0 pb-2', body: 'flex flex-col gap-5 pb-24', footer: 'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4' }"
  >
    <template #header>
      <div v-if="!response" class="flex w-full items-center gap-3.5">
        <USkeleton class="size-16 rounded-full" />
        <div class="flex flex-1 flex-col gap-2"><USkeleton class="h-5 w-48" /><USkeleton class="h-4 w-32" /></div>
      </div>
      <FormsResponsesDetailHeader v-else :response="response" :busy="busy" @status="status => save({ status })" @delete="remove" @close="open = false" />
    </template>

    <template #body>
      <div v-if="loading && !response" class="flex flex-col gap-4" :aria-label="t('common.loading')">
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3"><USkeleton v-for="n in 6" :key="n" class="h-14 rounded-lg" /></div>
        <USkeleton v-for="n in 4" :key="n" class="h-16 w-full rounded-lg" />
      </div>
      <UEmpty v-else-if="failed && !response" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" variant="naked" />

      <template v-else-if="response">
        <div class="flex flex-col gap-5 transition-opacity" :class="loading ? 'opacity-60' : ''" :aria-busy="loading || undefined">
          <FormsResponsesDetailFacts :response="response" />

          <UFormField :label="t('responses.detail.tags')">
            <UInputTags
              :model-value="response.tags"
              :placeholder="t('responses.detail.addTag')"
              :disabled="!response.can.review || busy"
              :max-length="40"
              icon="i-lucide-tag"
              class="w-full"
              @update:model-value="tags => save({ tags: tags as string[] })"
            />
          </UFormField>

          <UAlert
            v-if="response.possible_duplicate"
            icon="i-lucide-copy"
            color="warning"
            variant="subtle"
            :title="t('responses.detail.duplicateTitle')"
            :description="t('responses.detail.duplicateDesc')"
            :actions="[
              { label: t('responses.detail.openEarlier'), color: 'neutral', variant: 'outline', onClick: () => emit('go', response!.possible_duplicate!.of) },
              ...(response.can.review
                ? [
                    { label: t('responses.detail.notDuplicate'), color: 'neutral' as const, variant: 'outline' as const, loading: busy, onClick: () => save({ duplicate: 'cleared' }) },
                    { label: t('responses.detail.rejectDuplicate'), color: 'error' as const, variant: 'soft' as const, loading: busy, onClick: () => save({ status: 'rejected', tags: [...new Set([...response!.tags, 'duplicate'])] }) },
                  ]
                : []),
            ]"
          />

          <FormsResponsesDetailAnswers :response="response" @updated="value => ((response = value), emit('changed'))" />
          <FormsResponsesNotes :response="response" @updated="value => ((response = value), emit('changed'))" />
        </div>
      </template>
    </template>

    <!-- Floating previous / next -->
    <template #footer>
      <nav class="pointer-events-auto flex items-center gap-1 rounded-full border border-default bg-default/95 p-1 shadow-lg backdrop-blur" :aria-label="t('responses.detail.navigate')">
        <UButton
          :label="t('responses.detail.prevShort')"
          icon="i-lucide-arrow-up"
          color="neutral"
          variant="ghost"
          size="sm"
          class="rounded-full"
          :disabled="!prev"
          :aria-label="t('responses.detail.previous')"
          @click="prev && emit('go', prev)"
        >
          <template #trailing><UKbd value="K" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
        <span v-if="index >= 0" class="px-2 text-xs text-muted tabular-nums">{{ t('responses.detail.position', { n: index + 1, total: ids.length }) }}</span>
        <UButton
          :label="t('responses.detail.nextShort')"
          icon="i-lucide-arrow-down"
          color="neutral"
          variant="solid"
          size="sm"
          class="rounded-full"
          :disabled="!next"
          :aria-label="t('responses.detail.next')"
          @click="next && emit('go', next)"
        >
          <template #trailing><UKbd value="J" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
      </nav>
    </template>
  </USlideover>
</template>
